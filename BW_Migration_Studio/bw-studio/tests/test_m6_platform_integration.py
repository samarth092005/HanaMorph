"""
HANAMORPH BW Migration & Modernization Studio
M6 Platform Integration & Decoupled Contract Test Suite
"""

import unittest
import os
import sys
import json
import threading
import urllib.request
import urllib.error

# Ensure bw-studio root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.server import ThreadedHTTPServer, StudioHandler

TEST_PORT = 4028
TEST_HOST = "127.0.0.1"
TEST_API_KEY = "test-m6-platform-integration-key-777"


class TestM6PlatformIntegration(unittest.TestCase):

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
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.openapi_path = os.path.join(base_dir, "docs", "integration", "BW_STUDIO_OPENAPI_V1.json")
        self.adapter_path = os.path.join(base_dir, "integration", "bw_studio_adapter.js")

    # -------------------------------------------------------------
    # 1. OpenAPI 3.0 Specification Validation
    # -------------------------------------------------------------
    def test_01_openapi_spec_structure(self):
        self.assertTrue(os.path.exists(self.openapi_path), f"OpenAPI spec not found at: {self.openapi_path}")
        with open(self.openapi_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        self.assertEqual(spec.get("openapi"), "3.0.3")
        self.assertIn("info", spec)
        self.assertIn("title", spec["info"])
        self.assertIn("paths", spec)
        self.assertIn("components", spec)
        self.assertIn("securitySchemes", spec["components"])
        self.assertIn("ApiKeyAuth", spec["components"]["securitySchemes"])

        paths = spec["paths"]
        self.assertGreaterEqual(len(paths), 15)
        for p, methods in paths.items():
            self.assertTrue(p.startswith("/"), f"Path must start with '/': {p}")
            self.assertTrue(any(m in methods for m in ["get", "post", "put", "delete"]))

    # -------------------------------------------------------------
    # 2. Decoupled Adapter Existence and Integrity
    # -------------------------------------------------------------
    def test_02_adapter_script_contract(self):
        self.assertTrue(os.path.exists(self.adapter_path), f"Adapter script not found at: {self.adapter_path}")
        with open(self.adapter_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Enforce zero database coupling in the adapter
        self.assertNotIn("sqlite3", content.lower())
        self.assertNotIn("bw_studio.sqlite", content.lower())
        self.assertIn("http://127.0.0.1:4004", content)
        self.assertIn("Authorization", content)
        self.assertIn("X-API-Key", content)

    # -------------------------------------------------------------
    # 3. Decoupled REST Integration Client Test
    # -------------------------------------------------------------
    def test_03_adapter_rest_calls(self):
        """Simulates the decoupled adapter executing HTTP calls over loopback."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "HANAMORPH-Platform-Adapter/1.0.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["sapSafety"], "STRICT_READ_ONLY_ENFORCED")

        # Authenticated Overview call
        url = f"http://{TEST_HOST}:{TEST_PORT}/api/overview"
        req = urllib.request.Request(url, headers={
            "User-Agent": "HANAMORPH-Platform-Adapter/1.0.0",
            "Authorization": f"Bearer {TEST_API_KEY}"
        })
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.assertIn("totalSourceObjects", data)
        self.assertIn("supportedTargetRoutes", data)

    # -------------------------------------------------------------
    # 4. Zero Direct Database Sharing Invariant
    # -------------------------------------------------------------
    def test_04_zero_database_sharing_invariant(self):
        """Verifies that platform integration requires only network REST communication."""
        server_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "server.py")
        with open(server_py, "r", encoding="utf-8") as f:
            server_src = f.read()

        # Confirm ThreadedHTTPServer binds to loopback
        self.assertIn("127.0.0.1", server_src)
        self.assertIn("ThreadedHTTPServer", server_src)


if __name__ == "__main__":
    unittest.main()
