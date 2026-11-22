"""
HANAMORPH BW Migration & Modernization Studio
SQLite Database Hardening & Single-Writer Ingestion Queue
Milestone M1.3, M1.4 & M1 Condition Remediation (C-01 & C-02)
"""

import sqlite3
import queue
import threading
import time
import os
import logging
from typing import Dict, List, Optional, Any, Callable, Union

logger = logging.getLogger("hanamorph.sqlite_queue")

class QueueFullError(Exception):
    """Raised when the bounded ingestion queue exceeds maximum capacity under backpressure."""
    pass

class WriterError(Exception):
    """Raised when a non-transient write failure occurs in the database writer."""
    pass

class SingleWriterQueue:
    """
    Single-Writer Ingestion Queue Pattern for SQLite.
    Decouples parallel worker threads from SQLite transactions,
    guaranteeing that exactly one thread executes writes within WAL mode.
    
    Remediation Features (Condition C-01 & C-02):
    - Guaranteed connection cleanup through try/finally.
    - Deterministic lifecycle state management.
    - Dead-Letter Queue (DLQ) with per-item failure isolation.
    - Atomic batch transactions with automatic fallback to isolated per-item commits.
    - Synchronous and asynchronous arbitrary SQL write support for legacy engine consolidation.
    - Bounded in-memory buffer enforcing backpressure.
    - Transient busy retry with exponential backoff.
    - Graceful shutdown with queue drain and WAL checkpointing.
    - Verification of SQLite file integrity.
    """
    _instances: Dict[str, "SingleWriterQueue"] = {}
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_path: str, **kwargs) -> "SingleWriterQueue":
        """Singleton accessor per database path for centralized write ownership."""
        norm_path = os.path.abspath(db_path)
        with cls._instance_lock:
            if norm_path not in cls._instances:
                instance = cls(norm_path, **kwargs)
                instance.start()
                cls._instances[norm_path] = instance
            return cls._instances[norm_path]

    def __init__(
        self,
        db_path: str,
        maxsize: int = 5000,
        batch_size: int = 500,
        flush_interval_sec: float = 0.05,
        max_retries: int = 3
    ):
        self.db_path = db_path
        self.maxsize = maxsize
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self.max_retries = max_retries

        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._shutdown_event = threading.Event()
        self._writer_thread: Optional[threading.Thread] = None
        self._total_written = 0
        self._total_batches = 0
        self._last_error: Optional[Exception] = None
        self._is_running = False
        self._lock = threading.RLock()
        
        # Dead-Letter Queue for quarantined items
        self.dlq: List[Dict[str, Any]] = []

        # Initialize WAL mode on DB file
        self._init_wal_db()

    def _init_wal_db(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA busy_timeout = 10000;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        conn.close()

    def start(self):
        """Starts the dedicated single-writer background thread."""
        with self._lock:
            if self._is_running and self._writer_thread and self._writer_thread.is_alive():
                return
            self._shutdown_event.clear()
            self._is_running = True
            self._writer_thread = threading.Thread(
                target=self._writer_loop,
                name="HanaMorph-SingleWriter-Thread",
                daemon=True
            )
            self._writer_thread.start()
            logger.info("SingleWriterQueue started for %s (bounded maxsize=%d)", self.db_path, self.maxsize)

    def enqueue_object(self, canonical_obj_dict: Dict[str, Any], block: bool = True, timeout: float = 5.0):
        """Enqueues a canonical object dictionary for persistent ingestion."""
        try:
            self._queue.put({"type": "OBJECT", "payload": canonical_obj_dict}, block=block, timeout=timeout)
        except queue.Full:
            raise QueueFullError(
                f"Ingestion queue full (capacity {self.maxsize}). Backpressure throttling triggered."
            )

    def enqueue_field(self, field_dict: Dict[str, Any], block: bool = True, timeout: float = 5.0):
        """Enqueues a field dictionary."""
        try:
            self._queue.put({"type": "FIELD", "payload": field_dict}, block=block, timeout=timeout)
        except queue.Full:
            raise QueueFullError("Ingestion queue full for fields.")

    def enqueue_dependency(self, dep_dict: Dict[str, Any], block: bool = True, timeout: float = 5.0):
        """Enqueues a dependency edge dictionary."""
        try:
            self._queue.put({"type": "DEPENDENCY", "payload": dep_dict}, block=block, timeout=timeout)
        except queue.Full:
            raise QueueFullError("Ingestion queue full for dependencies.")

    def execute_write(
        self,
        sql: str,
        params: Union[tuple, list, dict] = (),
        wait: bool = True,
        timeout: float = 10.0
    ) -> Any:
        """
        Executes an arbitrary SQL write statement (INSERT/UPDATE/DELETE) via the single writer thread.
        If wait=True, blocks until write completes and returns result or raises WriterError.
        If wait=False, queues the write and returns immediately.
        """
        return self.execute_writes([(sql, params)], wait=wait, timeout=timeout)

    def execute_writes(
        self,
        statements: List[tuple],
        wait: bool = True,
        timeout: float = 15.0
    ) -> Any:
        """
        Executes multiple SQL write statements within an atomic transaction via the single writer thread.
        Statements is a list of (sql, params) tuples.
        """
        self._ensure_running()
        done_event = threading.Event() if wait else None
        res_container = {"result": None, "error": None}

        task = {
            "type": "SQL_BATCH",
            "payload": {
                "statements": statements,
                "done_event": done_event,
                "res_container": res_container
            }
        }

        try:
            self._queue.put(task, block=True, timeout=timeout)
        except queue.Full:
            raise QueueFullError("Ingestion queue full for SQL batch write execution.")

        if wait:
            signaled = done_event.wait(timeout=timeout)
            if not signaled:
                raise TimeoutError(f"SQL batch write timed out after {timeout} seconds ({len(statements)} stmts)")
            if res_container["error"]:
                raise WriterError(f"SQL batch write execution failed: {res_container['error']}")
            return res_container["result"]
        return None

    def _ensure_running(self):
        with self._lock:
            if not self._is_running or not self._writer_thread or not self._writer_thread.is_alive():
                self.start()

    def _writer_loop(self):
        """Single-writer execution loop running exclusively on its own dedicated thread."""
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode = WAL;")
            cur.execute("PRAGMA busy_timeout = 10000;")
            cur.execute("PRAGMA synchronous = NORMAL;")
            cur.execute("PRAGMA foreign_keys = ON;")

            while not self._shutdown_event.is_set() or not self._queue.empty():
                batch = []
                start_time = time.time()

                # Accumulate items up to batch_size or flush interval
                while len(batch) < self.batch_size:
                    timeout = max(0.001, self.flush_interval_sec - (time.time() - start_time))
                    try:
                        item = self._queue.get(timeout=timeout)
                        batch.append(item)
                    except queue.Empty:
                        break

                if batch:
                    self._process_batch_safely(conn, cur, batch)

            # Flush any remaining items upon shutdown signal
            remaining = []
            while not self._queue.empty():
                try:
                    remaining.append(self._queue.get_nowait())
                except queue.Empty:
                    break

            if remaining:
                self._process_batch_safely(conn, cur, remaining)

        except Exception as loop_err:
            logger.critical("Fatal unhandled exception in single-writer loop: %s", loop_err, exc_info=True)
            self._last_error = loop_err
        finally:
            with self._lock:
                self._is_running = False

            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except Exception as e:
                    logger.warning("Checkpoint during writer shutdown: %s", e)
                try:
                    conn.close()
                except Exception as e:
                    logger.error("Error closing single-writer connection: %s", e)

            logger.info("SingleWriterQueue loop exited. Total written: %d", self._total_written)

    def _process_batch_safely(self, conn: sqlite3.Connection, cur: sqlite3.Cursor, batch: List[Dict[str, Any]]):
        """
        Attempts to write the batch atomically. If an unrecoverable per-item error occurs,
        falls back to item-isolated mode to commit valid items and route failing items to DLQ.
        """
        try:
            self._write_batch_with_retry(conn, cur, batch)
            for item in batch:
                self._signal_item_done(item, result=True, error=None)
                self._queue.task_done()
        except Exception as batch_err:
            logger.warning("Batch write failed (%s). Falling back to item-isolated processing.", batch_err)
            self._process_batch_isolated(conn, cur, batch)

    def _process_batch_isolated(self, conn: sqlite3.Connection, cur: sqlite3.Cursor, batch: List[Dict[str, Any]]):
        """Processes each item in its own transaction to isolate corrupt items to DLQ."""
        for item in batch:
            try:
                cur.execute("BEGIN IMMEDIATE TRANSACTION;")
                self._execute_single_item(cur, item)
                conn.commit()
                self._total_written += 1
                self._signal_item_done(item, result=True, error=None)
            except Exception as item_err:
                conn.rollback()
                self._last_error = item_err
                dlq_entry = {
                    "item": item,
                    "error": str(item_err),
                    "error_type": type(item_err).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                with self._lock:
                    self.dlq.append(dlq_entry)
                logger.error("Item isolated to DLQ: %s (Error: %s)", item.get("type"), item_err)
                self._signal_item_done(item, result=None, error=item_err)
            finally:
                self._queue.task_done()

    def _signal_item_done(self, item: Dict[str, Any], result: Any, error: Optional[Exception]):
        if item.get("type") in ("SQL", "SQL_BATCH"):
            payload = item.get("payload", {})
            done_event = payload.get("done_event")
            res_container = payload.get("res_container")
            if res_container is not None:
                res_container["result"] = result
                res_container["error"] = error
            if done_event is not None:
                done_event.set()

    def _write_batch_with_retry(self, conn: sqlite3.Connection, cur: sqlite3.Cursor, batch: List[Dict[str, Any]]):
        """Executes batch upsert in an atomic transaction with exponential backoff on busy/locked."""
        for attempt in range(1, self.max_retries + 1):
            try:
                cur.execute("BEGIN IMMEDIATE TRANSACTION;")
                for item in batch:
                    self._execute_single_item(cur, item)
                conn.commit()
                self._total_written += len(batch)
                self._total_batches += 1
                return
            except sqlite3.OperationalError as e:
                conn.rollback()
                self._last_error = e
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    if attempt < self.max_retries:
                        sleep_time = 0.05 * (2 ** (attempt - 1))
                        time.sleep(sleep_time)
                        continue
                logger.error("Failed batch write on attempt %d: %s", attempt, e)
                raise
            except Exception as e:
                conn.rollback()
                self._last_error = e
                logger.error("Non-retryable batch write error: %s", e)
                raise

    def _execute_single_item(self, cur: sqlite3.Cursor, item: Dict[str, Any]):
        item_type = item["type"]
        payload = item["payload"]
        if item_type == "OBJECT":
            self._upsert_object(cur, payload)
        elif item_type == "FIELD":
            self._upsert_field(cur, payload)
        elif item_type == "DEPENDENCY":
            self._upsert_dependency(cur, payload)
        elif item_type == "SQL":
            sql = payload["sql"]
            params = payload.get("params", ())
            cur.execute(sql, params)
        elif item_type == "SQL_BATCH":
            for sql, params in payload.get("statements", []):
                cur.execute(sql, params)
        else:
            raise ValueError(f"Unknown queue item type: '{item_type}'")

    def _upsert_object(self, cur: sqlite3.Cursor, p: Dict[str, Any]):
        cur.execute("""
            INSERT INTO canonical_bw_objects (
                urn, stable_urn, system_id, client, object_type, technical_name, version,
                description, infoarea, package, active_status, content_fingerprint,
                provenance, confidence_score, completeness_score, extracted_at, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(urn) DO UPDATE SET
                description = excluded.description,
                infoarea = excluded.infoarea,
                package = excluded.package,
                active_status = excluded.active_status,
                content_fingerprint = excluded.content_fingerprint,
                provenance = excluded.provenance,
                confidence_score = excluded.confidence_score,
                completeness_score = excluded.completeness_score,
                extracted_at = excluded.extracted_at,
                raw_payload = excluded.raw_payload;
        """, (
            p["urn"], p["stable_urn"], p["system_id"], p["client"], p["object_type"],
            p["technical_name"], p.get("version", "A"), p.get("description", ""),
            p.get("infoarea", ""), p.get("package", "$TMP"), p.get("active_status", "A"),
            p["content_fingerprint"], p.get("provenance", "LIVE_VERIFIED"),
            float(p.get("confidence_score", 1.0)), float(p.get("completeness_score", 1.0)),
            p.get("extracted_at", time.strftime("%Y-%m-%d %H:%M:%S")),
            p.get("raw_payload", "")
        ))

    def _upsert_field(self, cur: sqlite3.Cursor, p: Dict[str, Any]):
        cur.execute("""
            INSERT INTO canonical_object_fields (
                object_urn, field_name, data_type, position, length, decimals,
                is_key, aggregation, semantics, currency_unit_field, compounding_parent, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_urn, field_name) DO UPDATE SET
                data_type = excluded.data_type,
                position = excluded.position,
                length = excluded.length,
                decimals = excluded.decimals,
                is_key = excluded.is_key,
                aggregation = excluded.aggregation,
                semantics = excluded.semantics,
                currency_unit_field = excluded.currency_unit_field,
                compounding_parent = excluded.compounding_parent,
                description = excluded.description;
        """, (
            p["object_urn"], p["field_name"], p["data_type"], p.get("position", 0),
            p.get("length", 0), p.get("decimals", 0), 1 if p.get("is_key") else 0,
            p.get("aggregation", "NONE"), p.get("semantics"), p.get("currency_unit_field"),
            p.get("compounding_parent"), p.get("description", "")
        ))

    def _upsert_dependency(self, cur: sqlite3.Cursor, p: Dict[str, Any]):
        cur.execute("""
            INSERT INTO canonical_dependencies (
                source_urn, target_urn, dependency_type, is_hard_dependency, mapping_details
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_urn, target_urn, dependency_type) DO UPDATE SET
                is_hard_dependency = excluded.is_hard_dependency,
                mapping_details = excluded.mapping_details;
        """, (
            p["source_urn"], p["target_urn"], p["dependency_type"],
            1 if p.get("is_hard_dependency", True) else 0,
            p.get("mapping_details", "")
        ))

    def stop(self, timeout: float = 10.0):
        """Signals shutdown, drains queue, and joins the single writer thread."""
        with self._lock:
            if not self._is_running:
                return
            self._shutdown_event.set()

        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=timeout)

    def checkpoint(self, mode: str = "TRUNCATE") -> dict:
        """Executes a WAL checkpoint on the database."""
        mode_upper = mode.upper()
        if mode_upper not in ["PASSIVE", "FULL", "RESTART", "TRUNCATE"]:
            mode_upper = "TRUNCATE"
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cur = conn.cursor()
        cur.execute(f"PRAGMA wal_checkpoint({mode_upper});")
        row = cur.fetchone()
        conn.close()
        return {
            "mode": mode_upper,
            "busy": row[0] if row else 0,
            "log_frames": row[1] if row else 0,
            "checkpointed_frames": row[2] if row else 0
        }

    def verify_integrity(self) -> bool:
        """Executes PRAGMA integrity_check to verify database consistency."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return len(rows) == 1 and rows[0] == "ok"

    def get_dlq(self) -> List[Dict[str, Any]]:
        """Returns copies of all entries currently in Dead-Letter Queue."""
        with self._lock:
            return list(self.dlq)

    def clear_dlq(self):
        """Clears the Dead-Letter Queue."""
        with self._lock:
            self.dlq.clear()

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def total_written(self) -> int:
        return self._total_written

    @property
    def dlq_count(self) -> int:
        with self._lock:
            return len(self.dlq)

def get_writer_queue(db_path: str) -> SingleWriterQueue:
    """Canonical accessor for centralized database writes."""
    return SingleWriterQueue.get_instance(db_path)

def get_read_connection(db_path: str) -> sqlite3.Connection:
    """Canonical accessor for concurrent WAL read connections."""
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

