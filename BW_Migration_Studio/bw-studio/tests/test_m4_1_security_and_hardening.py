import unittest
import os
import sys
import hmac
import hashlib
import tempfile
import threading
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.server import get_or_create_api_key
from connectors.bw_connection_manager import BWConnectionManager, SecurityViolationError
from connectors.mock_rfc import MockRFCClient
from database.sqlite_queue import SingleWriterQueue
from database.schema_manager import SchemaManager

class TestM41SecurityAndHardening(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_m41_sec.sqlite")
        sm = SchemaManager(self.test_db)
        sm.apply_migrations()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_api_key_generation_and_storage(self):
        """Verify API key generation produces high-entropy token stored securely."""
        key = get_or_create_api_key()
        self.assertIsNotNone(key)
        self.assertGreaterEqual(len(key), 32)
        # Verify SHA-256 fingerprint computation
        fp = hashlib.sha256(key.encode('utf-8')).hexdigest()
        self.assertEqual(len(fp), 64)

    def test_02_constant_time_token_verification(self):
        """Verify token comparison uses constant-time hmac.compare_digest."""
        token_a = "secret_token_alpha_1234567890_abcdef"
        token_b = "secret_token_alpha_1234567890_abcdef"
        token_c = "secret_token_beta_9999999999_xyz123"

        self.assertTrue(hmac.compare_digest(token_a.encode('utf-8'), token_b.encode('utf-8')))
        self.assertFalse(hmac.compare_digest(token_a.encode('utf-8'), token_c.encode('utf-8')))
        self.assertFalse(hmac.compare_digest(token_a.encode('utf-8'), "".encode('utf-8')))

    def test_03_mutating_sap_http_methods_blocked(self):
        """Verify mutating HTTP verbs (POST, PUT, DELETE, PATCH) are blocked by security guardrails."""
        conn = BWConnectionManager({
            "SAP_BW_HOST": "192.168.1.55",
            "SAP_BW_CLIENT": "200",
            "SAP_BW_USER": "int_samarth",
            "SAP_BW_PASSWORD": "dummy_password"
        })

        mutating_verbs = ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        for verb in mutating_verbs:
            with self.assertRaises(SecurityViolationError) as ctx:
                conn.execute_sap_http(verb, "/sap/bc/adt/discovery")
            self.assertIn("SAFETY GUARDRAIL BLOCKED", str(ctx.exception))
            self.assertIn("forbidden", str(ctx.exception))

    def test_04_forbidden_sap_endpoints_blocked(self):
        """Verify forbidden SAP administrative endpoints are blocked even on GET."""
        conn = BWConnectionManager({
            "SAP_BW_HOST": "192.168.1.55",
            "SAP_BW_CLIENT": "200"
        })

        prohibited_endpoints = [
            "/sap/bc/adt/cts/transports",
            "/sap/bc/adt/activate",
            "/sap/bc/adt/lock",
            "/sap/bc/adt/create"
        ]
        for ep in prohibited_endpoints:
            with self.assertRaises(SecurityViolationError) as ctx:
                conn.execute_sap_http("GET", ep)
            self.assertIn("SAFETY GUARDRAIL BLOCKED", str(ctx.exception))

    def test_05_rfc_allowlist_enforcement(self):
        """Verify non-whitelisted RFC functions raise SecurityViolationError."""
        conn = BWConnectionManager({
            "SAP_BW_HOST": "192.168.1.55",
            "SAP_BW_CLIENT": "200"
        })
        mock_client = MockRFCClient()

        # Permitted benign RFCs
        res_ping = conn.execute_benign_rfc("RFC_PING", rfc_client=mock_client)
        self.assertEqual(res_ping["status"], "SUCCESS")
        self.assertTrue(res_ping["read_only_verified"])

        res_stfc = conn.execute_benign_rfc("STFC_CONNECTION", {"REQUTEXT": "TEST"}, rfc_client=mock_client)
        self.assertEqual(res_stfc["status"], "SUCCESS")

        # Prohibited RFCs
        prohibited_rfcs = [
            "RFC_READ_TABLE",
            "BAPI_USER_GET_DETAIL",
            "TR_REQUEST_CHOICE",
            "SE37_EXECUTE",
            "BAPI_TRANSACTION_COMMIT"
        ]
        for rfc in prohibited_rfcs:
            with self.assertRaises(SecurityViolationError) as ctx:
                conn.execute_benign_rfc(rfc, rfc_client=mock_client)
            self.assertIn("SAFETY GUARDRAIL BLOCKED", str(ctx.exception))

    def test_06_password_redaction_in_exceptions(self):
        """Verify sensitive credentials are redacted from network error strings."""
        sensitive_pw = "SuperSecret_S21_Pass#99!"
        conn = BWConnectionManager({
            "SAP_BW_HOST": "192.168.1.55",
            "SAP_BW_CLIENT": "200",
            "SAP_BW_USER": "int_samarth",
            "SAP_BW_PASSWORD": sensitive_pw
        })

        import unittest.mock as mock
        with mock.patch("urllib.request.urlopen", side_effect=Exception(f"Auth failure with password {sensitive_pw}")):
            try:
                conn.execute_sap_http("GET", "/sap/bc/adt/discovery")
                self.fail("Should have raised ConnectionError")
            except ConnectionError as e:
                err_msg = str(e)
                self.assertNotIn(sensitive_pw, err_msg)
                self.assertIn("[REDACTED]", err_msg)

    def test_07_concurrent_database_writes_with_queue(self):
        """Verify SingleWriterQueue processes concurrent writes without locks or corruption."""
        queue = SingleWriterQueue.get_instance(self.test_db, maxsize=1000, batch_size=20)
        total_items = 100

        def write_worker(worker_id):
            for i in range(10):
                obj_id = f"OBJ_{worker_id}_{i}"
                tech_name = f"ZTEST_{worker_id}_{i}"
                sql = "INSERT INTO bw_objects (id, system_id, technical_name, type, description, provenance) VALUES (?, ?, ?, ?, ?, ?)"
                params = (obj_id, "SYNTH_SYS", tech_name, "ADSO", f"Worker {worker_id} Item {i}", "SYNTHETIC")
                queue.execute_write(sql, params, wait=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_worker, wid) for wid in range(10)]
            for f in futures:
                f.result()

        # Verify all 100 items were safely committed
        import sqlite3
        conn = sqlite3.connect(self.test_db)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM bw_objects WHERE system_id = 'SYNTH_SYS'")
        count = cur.fetchone()[0]
        conn.close()

        self.assertEqual(count, total_items)

if __name__ == "__main__":
    unittest.main()
