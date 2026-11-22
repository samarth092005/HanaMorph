"""
HANAMORPH BW Migration & Modernization Studio
Database Backup, Integrity & Disaster Recovery Manager
Milestone M5
"""

import sqlite3
import os
import hashlib
import time
from typing import Dict, Any, Optional

class DatabaseBackupManager:
    """
    Manages non-blocking SQLite backups, integrity audits,
    WAL checkpointing, and disaster recovery restoration.
    """

    def __init__(self, db_path: str, backup_dir: Optional[str] = None):
        self.db_path = db_path
        self.backup_dir = backup_dir or os.path.join(os.path.dirname(db_path), "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_atomic_backup(self, tag: str = "auto") -> Dict[str, Any]:
        """Creates a non-blocking hot backup using SQLite Online Backup API."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Source database not found: {self.db_path}")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_filename = f"bw_studio_{tag}_{timestamp}.sqlite"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        src_conn = sqlite3.connect(self.db_path)
        dst_conn = sqlite3.connect(backup_path)

        with dst_conn:
            src_conn.backup(dst_conn, pages=100)

        dst_conn.close()
        src_conn.close()

        # Compute SHA-256 and size
        with open(backup_path, "rb") as f:
            content = f.read()
        sha = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)

        # Verify integrity of the newly created backup
        integrity_ok, check_msg = self.verify_integrity(backup_path)

        return {
            "backup_file": backup_filename,
            "backup_path": backup_path,
            "size_bytes": size_bytes,
            "sha256": sha,
            "integrity_verified": integrity_ok,
            "integrity_message": check_msg,
            "timestamp": timestamp
        }

    def verify_integrity(self, target_db_path: Optional[str] = None) -> tuple:
        """Runs PRAGMA integrity_check on the specified database."""
        path = target_db_path or self.db_path
        if not os.path.exists(path):
            return False, f"Database does not exist: {path}"

        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchall()
        conn.close()

        if len(res) == 1 and res[0][0] == "ok":
            return True, "ok"
        return False, "; ".join([r[0] for r in res])

    def checkpoint_wal(self) -> Dict[str, Any]:
        """Forces WAL checkpoint truncation to optimize disk footprint."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        res = cur.fetchone()
        conn.close()
        return {
            "busy": res[0],
            "log_frames": res[1],
            "checkpointed_frames": res[2]
        }

    def restore_backup(
        self,
        source_backup_path: str,
        destination_path: str,
        verify: bool = True
    ) -> Dict[str, Any]:
        """
        Controlled disaster recovery restore.
        Restores a verified SQLite backup to a separate destination path.
        Strictly prohibits overwriting the active live database.
        """
        if not source_backup_path or not os.path.exists(source_backup_path):
            raise FileNotFoundError(f"Source backup file not found: {source_backup_path}")

        # Prohibit overwriting active database
        real_src = os.path.realpath(source_backup_path)
        real_dst = os.path.realpath(destination_path)
        real_active = os.path.realpath(self.db_path)

        if real_dst == real_active:
            raise PermissionError(
                "Restoring directly over the active database is prohibited for data safety. "
                "Specify a separate destination path."
            )

        if real_src == real_dst:
            raise ValueError("Source backup path and destination path cannot be identical.")

        if os.path.exists(destination_path):
            raise FileExistsError(
                f"Destination path already exists: {destination_path}. "
                "Specify a new destination path to avoid accidental data loss."
            )

        # Verify integrity of backup file before restore
        integrity_ok, integrity_msg = self.verify_integrity(source_backup_path)
        if not integrity_ok:
            raise ValueError(f"Source backup failed integrity check: {integrity_msg}")

        # Ensure destination directory exists
        dst_dir = os.path.dirname(destination_path)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)

        # Execute safe online backup copy to destination
        src_conn = sqlite3.connect(source_backup_path)
        dst_conn = sqlite3.connect(destination_path)

        with dst_conn:
            src_conn.backup(dst_conn, pages=100)

        dst_conn.close()
        src_conn.close()

        # Validate restored database integrity and schema
        dst_ok, dst_msg = self.verify_integrity(destination_path)
        if not dst_ok:
            raise RuntimeError(f"Restored database failed integrity check: {dst_msg}")

        # Inspect table counts and schema
        conn = sqlite3.connect(destination_path)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        table_count = cur.fetchone()[0]
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()

        # Compute SHA-256 hashes
        with open(source_backup_path, "rb") as f:
            src_sha = hashlib.sha256(f.read()).hexdigest()
        with open(destination_path, "rb") as f:
            dst_sha = hashlib.sha256(f.read()).hexdigest()

        return {
            "status": "RESTORED_AND_VERIFIED",
            "source_backup_path": source_backup_path,
            "destination_path": destination_path,
            "source_sha256": src_sha,
            "destination_sha256": dst_sha,
            "integrity_verified": dst_ok,
            "table_count": table_count,
            "restored_tables": tables,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
