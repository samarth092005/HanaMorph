"""
HANAMORPH BW Migration & Modernization Studio
Persistent Background Job Engine
Milestone M5
"""

import sqlite3
import json
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Callable
from database.sqlite_queue import SingleWriterQueue

class JobStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class BackgroundJobEngine:
    """
    Persistent SQLite-backed background job processing engine.
    Ensures long-running tasks execute asynchronously without blocking HTTP workers.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_path: str, max_workers: int = 4):
        with cls._lock:
            if cls._instance is None:
                cls._instance = BackgroundJobEngine(db_path, max_workers)
            return cls._instance

    def __init__(self, db_path: str, max_workers: int = 4):
        self.db_path = db_path
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="JobWorker")
        self.active_jobs: Dict[str, threading.Event] = {}
        self._init_db()
        self.reconciled_at_startup = self.reconcile_orphaned_jobs()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS background_jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                progress_pct INTEGER DEFAULT 0,
                payload TEXT,
                result TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def reconcile_orphaned_jobs(self, target_status: str = JobStatus.FAILED) -> List[Dict[str, Any]]:
        """
        Reconciles orphaned jobs stuck in RUNNING status from previous ungraceful shutdown.
        Safely marks them as FAILED (or target_status) with clear recovery metadata.
        Does not automatically re-execute non-idempotent operations.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, job_type, started_at FROM background_jobs WHERE status = 'RUNNING'")
        orphans = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not orphans:
            return []

        queue = SingleWriterQueue.get_instance(self.db_path)
        for job in orphans:
            job_id = job["id"]
            err_msg = (
                f"Job interrupted by process termination / ungraceful shutdown. "
                f"Reconciled on startup (was RUNNING since {job.get('started_at')})."
            )
            queue.execute_write("""
                UPDATE background_jobs
                SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'RUNNING'
            """, (target_status, err_msg, job_id), wait=True)
        return orphans

    def submit_job(self, job_type: str, payload: Dict[str, Any], task_fn: Callable[[str, Dict[str, Any], threading.Event], Any]) -> str:
        """Submits a job to the persistent queue and begins execution."""
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        cancel_event = threading.Event()
        self.active_jobs[job_id] = cancel_event

        payload_json = json.dumps(payload)
        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_write("""
            INSERT INTO background_jobs (id, job_type, status, progress_pct, payload, created_at)
            VALUES (?, ?, 'QUEUED', 0, ?, CURRENT_TIMESTAMP)
        """, (job_id, job_type, payload_json), wait=True)

        self.executor.submit(self._worker_wrapper, job_id, payload, task_fn, cancel_event)
        return job_id

    def _worker_wrapper(self, job_id: str, payload: Dict[str, Any], task_fn: Callable, cancel_event: threading.Event):
        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_write("""
            UPDATE background_jobs
            SET status = 'RUNNING', started_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (job_id,), wait=True)

        try:
            if cancel_event.is_set():
                queue.execute_write("""
                    UPDATE background_jobs
                    SET status = 'CANCELLED', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (job_id,), wait=True)
                return

            # Execute task function
            res = task_fn(job_id, payload, cancel_event)
            res_json = json.dumps(res) if res is not None else "{}"

            if cancel_event.is_set():
                status = JobStatus.CANCELLED
            else:
                status = JobStatus.COMPLETED

            queue.execute_write("""
                UPDATE background_jobs
                SET status = ?, progress_pct = 100, result = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, res_json, job_id), wait=True)

        except Exception as e:
            queue.execute_write("""
                UPDATE background_jobs
                SET status = 'FAILED', error_message = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (str(e), job_id), wait=True)
        finally:
            self.active_jobs.pop(job_id, None)

    def update_progress(self, job_id: str, progress_pct: int):
        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_write("""
            UPDATE background_jobs
            SET progress_pct = ?
            WHERE id = ?
        """, (progress_pct, job_id), wait=False)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM background_jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        if d.get("payload"):
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                pass
        if d.get("result"):
            try:
                d["result"] = json.loads(d["result"])
            except Exception:
                pass
        return d

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM background_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get("payload"):
                try:
                    r["payload"] = json.loads(r["payload"])
                except Exception:
                    pass
            if r.get("result"):
                try:
                    r["result"] = json.loads(r["result"])
                except Exception:
                    pass
        return rows

    def cancel_job(self, job_id: str) -> bool:
        cancel_event = self.active_jobs.get(job_id)
        if cancel_event:
            cancel_event.set()
            queue = SingleWriterQueue.get_instance(self.db_path)
            queue.execute_write("""
                UPDATE background_jobs
                SET status = 'CANCELLED', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (job_id,), wait=True)
            return True
        return False
