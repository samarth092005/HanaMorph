import unittest
import subprocess
import time
import urllib.request
import urllib.error
import json
import os
import sys
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_SCRIPT = os.path.join(BASE_DIR, "backend", "server.py")

class TestServerLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_key = "test-live-server-api-key-999888777"
        env = dict(os.environ, BW_STUDIO_API_KEY=cls.api_key)
        cls.proc = subprocess.Popen([sys.executable, SERVER_SCRIPT], env=env)
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        if cls.proc:
            cls.proc.terminate()
            cls.proc.wait()

    def _auth_headers(self, additional=None):
        h = {"Authorization": f"Bearer {self.api_key}", "X-API-Key": self.api_key}
        if additional:
            h.update(additional)
        return h

    def test_01_health_check(self):
        with urllib.request.urlopen("http://localhost:4004/health", timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data["status"], "HEALTHY")
            self.assertEqual(data["service"], "BW_Migration_Studio")
            self.assertEqual(data["authMode"], "API_KEY")

    def test_02_overview(self):
        req = urllib.request.Request("http://localhost:4004/api/overview", headers=self._auth_headers())
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            self.assertGreaterEqual(data["totalSourceObjects"], 5)
            self.assertEqual(data["s21Inspection"], "READ_ONLY_VERIFIED")

    def test_03_assessment_single(self):
        req = urllib.request.Request(
            "http://localhost:4004/api/assess",
            data=json.dumps({"objectName": "ZSAM_SO01"}).encode('utf-8'),
            headers=self._auth_headers({"Content-Type": "application/json"})
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            self.assertIn("Native Datasphere", data["recommendedRoute"])

    def test_04_connections_list(self):
        req = urllib.request.Request("http://localhost:4004/api/connections", headers=self._auth_headers())
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(len(data), 5)

    def test_05_connections_test_bw_s21(self):
        req = urllib.request.Request(
            "http://localhost:4004/api/connections/test",
            data=json.dumps({"systemId": "bw_s21"}).encode('utf-8'),
            headers=self._auth_headers({"Content-Type": "application/json"})
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            self.assertIn(data["status"], ["CONNECTED", "NOT CONFIGURED", "FAILED"])

    def test_06_traversal_blocked(self):
        # Attempt path traversal
        for traversal_path in [
            "http://localhost:4004/../backend/server.py",
            "http://localhost:4004/..%2fbackend%2fserver.py",
            "http://localhost:4004/../../database/bw_studio.sqlite"
        ]:
            try:
                urllib.request.urlopen(traversal_path, timeout=5)
                self.fail(f"Path traversal should have failed: {traversal_path}")
            except urllib.error.HTTPError as e:
                self.assertIn(e.code, [403, 404])

    def test_07_sensitive_files_blocked(self):
        for sensitive_path in [
            "http://localhost:4004/.env",
            "http://localhost:4004/.api_key",
            "http://localhost:4004/bw_studio.sqlite",
            "http://localhost:4004/database/bw_studio.sqlite",
            "http://localhost:4004/server.py"
        ]:
            try:
                urllib.request.urlopen(sensitive_path, timeout=5)
                self.fail(f"Access to sensitive file should have failed: {sensitive_path}")
            except urllib.error.HTTPError as e:
                self.assertIn(e.code, [403, 404])

    def test_08_unknown_endpoint_json_404(self):
        req = urllib.request.Request("http://localhost:4004/api/unknown/resource", headers=self._auth_headers())
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("Unknown API route should return 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            data = json.loads(e.read().decode('utf-8'))
            self.assertEqual(data.get("status"), "ERROR")

    def test_09_missing_token_unauthorized_401(self):
        req = urllib.request.Request("http://localhost:4004/api/overview")
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("Request without token should fail with 401")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)
            data = json.loads(e.read().decode('utf-8'))
            self.assertEqual(data.get("status"), "UNAUTHORIZED")
            self.assertIn("Missing authentication credentials", data.get("error", ""))

    def test_10_invalid_token_unauthorized_401(self):
        req = urllib.request.Request(
            "http://localhost:4004/api/overview",
            headers={"Authorization": "Bearer invalid_secret_token_12345"}
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("Request with invalid token should fail with 401")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)
            data = json.loads(e.read().decode('utf-8'))
            self.assertEqual(data.get("status"), "UNAUTHORIZED")
            self.assertIn("Invalid API token", data.get("error", ""))

    def test_11_valid_token_bearer_and_x_api_key(self):
        # Test Bearer header
        req_bearer = urllib.request.Request(
            "http://localhost:4004/api/overview",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        with urllib.request.urlopen(req_bearer, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

        # Test X-API-Key header
        req_x_key = urllib.request.Request(
            "http://localhost:4004/api/overview",
            headers={"X-API-Key": self.api_key}
        )
        with urllib.request.urlopen(req_x_key, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

    def test_12_public_health_endpoints_without_auth(self):
        # /health
        with urllib.request.urlopen("http://localhost:4004/health", timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data["status"], "HEALTHY")

        # /api/health
        with urllib.request.urlopen("http://localhost:4004/api/health", timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data["status"], "HEALTHY")

    def test_13_cors_preflight_options(self):
        req = urllib.request.Request("http://localhost:4004/api/overview", method="OPTIONS")
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            headers = resp.headers
            self.assertIn("Access-Control-Allow-Origin", headers)
            self.assertIn("Authorization", headers.get("Access-Control-Allow-Headers", ""))

    def test_14_concurrent_requests_non_blocking(self):
        # Fire 12 concurrent requests simultaneously across a thread pool
        def fetch_endpoint(url, use_auth=True):
            headers = self._auth_headers() if use_auth else {}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode('utf-8'))

        urls = [
            ("http://localhost:4004/health", False),
            ("http://localhost:4004/api/health", False),
            ("http://localhost:4004/api/overview", True),
            ("http://localhost:4004/api/connections", True),
            ("http://localhost:4004/health", False),
            ("http://localhost:4004/api/overview", True),
            ("http://localhost:4004/health", False),
            ("http://localhost:4004/api/connections", True),
            ("http://localhost:4004/api/overview", True),
            ("http://localhost:4004/health", False),
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(fetch_endpoint, u, auth) for u, auth in urls]
            results = [f.result() for f in futures]

        for status, data in results:
            self.assertEqual(status, 200)
            self.assertTrue("status" in data or "totalSourceObjects" in data or isinstance(data, list))

if __name__ == "__main__":
    unittest.main()
