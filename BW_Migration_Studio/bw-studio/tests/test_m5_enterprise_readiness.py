"""
HANAMORPH BW Migration & Modernization Studio
M5 Enterprise Product Readiness Test Suite
"""

import unittest
import os
import sys
import json
import time
import io
import tempfile
import shutil
import threading
import urllib.request
import urllib.error

# Ensure bw-studio root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.job_engine import BackgroundJobEngine, JobStatus
from core.structured_logger import StructuredLogger
from core.database_backup_manager import DatabaseBackupManager
from backend.server import ThreadedHTTPServer, StudioHandler

TEST_PORT = 4022
TEST_HOST = "127.0.0.1"
TEST_API_KEY = "test-m5-enterprise-api-key-888"


class TestM5EnterpriseReadiness(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["BW_STUDIO_API_KEY"] = TEST_API_KEY
        cls.httpd = ThreadedHTTPServer((TEST_HOST, TEST_PORT), StudioHandler, api_key=TEST_API_KEY)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_m5.sqlite")
        self.job_engine = BackgroundJobEngine(self.db_path, max_workers=2)
        self.backup_mgr = DatabaseBackupManager(self.db_path, backup_dir=os.path.join(self.temp_dir, "backups"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _request(self, method: str, path: str, payload=None):
        url = f"http://{TEST_HOST}:{TEST_PORT}{path}"
        data = json.dumps(payload).encode("utf-8") if payload else None
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TEST_API_KEY}"
        }
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}

    # -------------------------------------------------------------
    # 1. Background Job Engine Tests
    # -------------------------------------------------------------
    def test_01_job_submission_and_completion(self):
        def sample_work(jid, p, cancel_evt):
            self.job_engine.update_progress(jid, 50)
            return {"count": p.get("records", 0) * 2}

        job_id = self.job_engine.submit_job("UNIT_TEST_TASK", {"records": 25}, sample_work)
        self.assertTrue(job_id.startswith("job-"))

        # Wait for completion (up to 3 seconds)
        for _ in range(30):
            job = self.job_engine.get_job(job_id)
            if job and job["status"] == JobStatus.COMPLETED:
                break
            time.sleep(0.1)

        self.assertEqual(job["status"], JobStatus.COMPLETED)
        self.assertEqual(job["progress_pct"], 100)
        self.assertEqual(job["result"]["count"], 50)

    def test_02_job_cancellation(self):
        def slow_task(jid, p, cancel_evt):
            for _ in range(50):
                if cancel_evt.is_set():
                    return {"interrupted": True}
                time.sleep(0.05)
            return {"interrupted": False}

        job_id = self.job_engine.submit_job("SLOW_TASK", {}, slow_task)
        time.sleep(0.05) # Allow worker to start
        cancelled = self.job_engine.cancel_job(job_id)
        self.assertTrue(cancelled)

        time.sleep(0.2)
        job = self.job_engine.get_job(job_id)
        self.assertEqual(job["status"], JobStatus.CANCELLED)

    # -------------------------------------------------------------
    # 2. Structured JSON Logger Tests
    # -------------------------------------------------------------
    def test_03_structured_logger_formatting_and_redaction(self):
        buffer = io.StringIO()
        logger = StructuredLogger(component="SECURITY_AUDIT", stream=buffer)

        logger.info(
            "Connection attempt to S21",
            trace_id="tr-12345",
            password="SuperSecretPassword!",
            user="int_samarth",
            endpoint="/sap/bc/adt/discovery"
        )

        output = buffer.getvalue().strip()
        record = json.loads(output)

        self.assertEqual(record["level"], "INFO")
        self.assertEqual(record["component"], "SECURITY_AUDIT")
        self.assertEqual(record["trace_id"], "tr-12345")
        self.assertEqual(record["extra"]["password"], "[REDACTED]")
        self.assertEqual(record["extra"]["user"], "int_samarth")
        self.assertNotIn("SuperSecretPassword!", output)

    # -------------------------------------------------------------
    # 3. Database Backup & Disaster Recovery Tests
    # -------------------------------------------------------------
    def test_04_atomic_backup_and_integrity_check(self):
        backup_res = self.backup_mgr.create_atomic_backup(tag="test_drill")
        self.assertTrue(backup_res["integrity_verified"])
        self.assertEqual(backup_res["integrity_message"], "ok")
        self.assertTrue(os.path.exists(backup_res["backup_path"]))
        self.assertGreater(backup_res["size_bytes"], 0)
        self.assertEqual(len(backup_res["sha256"]), 64)

    def test_05_wal_checkpoint(self):
        res = self.backup_mgr.checkpoint_wal()
        self.assertIn("busy", res)
        self.assertIn("checkpointed_frames", res)

    # -------------------------------------------------------------
    # 4. Enterprise API Endpoints Integration Tests
    # -------------------------------------------------------------
    def test_06_api_job_lifecycle(self):
        status, submit_res = self._request("POST", "/api/jobs/submit", {"jobType": "ASYNC_DISCOVERY"})
        self.assertEqual(status, 200)
        self.assertIn("jobId", submit_res)
        job_id = submit_res["jobId"]

        status, job_list = self._request("GET", "/api/jobs")
        self.assertEqual(status, 200)
        self.assertIsInstance(job_list, list)

        time.sleep(0.3)
        status, job_details = self._request("GET", f"/api/jobs/{job_id}")
        self.assertEqual(status, 200)
        self.assertIn("status", job_details)

    def test_07_api_admin_backup(self):
        status, backup_res = self._request("POST", "/api/admin/backup", {})
        self.assertEqual(status, 200)
        self.assertTrue(backup_res["integrity_verified"])
        self.assertEqual(len(backup_res["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
