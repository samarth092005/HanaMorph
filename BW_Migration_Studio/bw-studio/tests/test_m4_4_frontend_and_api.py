"""
HANAMORPH BW Migration & Modernization Studio
M4.4 Frontend Workflow & 12-Screen API Integration Test Suite
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

TEST_PORT = 4015
TEST_HOST = "127.0.0.1"
TEST_API_KEY = "test-m4-4-secret-api-key-999"


class TestM44FrontendAndAPI(unittest.TestCase):

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

    def _request(self, method: str, path: str, payload=None, api_key=TEST_API_KEY):
        url = f"http://{TEST_HOST}:{TEST_PORT}{path}"
        data = json.dumps(payload).encode("utf-8") if payload else None
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                return status, json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    # -------------------------------------------------------------
    # 1. Screen 1: Studio Overview Dashboard
    # -------------------------------------------------------------
    def test_01_screen_overview_api(self):
        status, data = self._request("GET", "/api/overview")
        self.assertEqual(status, 200)
        self.assertIn("totalSourceObjects", data)
        self.assertIn("s21Inspection", data)
        self.assertIn("supportedTargetRoutes", data)

    # -------------------------------------------------------------
    # 2. Screen 2: Landscape & S21 Connection Hub
    # -------------------------------------------------------------
    def test_02_screen_connections_api(self):
        status, data = self._request("GET", "/api/connections")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

        status, test_res = self._request("POST", "/api/connections/test", {"systemId": "all"})
        self.assertEqual(status, 200)

    # -------------------------------------------------------------
    # 3. Screen 3: Object Catalog & Discovery
    # -------------------------------------------------------------
    def test_03_screen_catalog_api(self):
        status, data = self._request("GET", "/api/catalog")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    # -------------------------------------------------------------
    # 4. Screen 4: Object Detail & DDIC Fields
    # -------------------------------------------------------------
    def test_04_screen_object_detail_api(self):
        # Fetch first catalog object or test with known object
        status, cat = self._request("GET", "/api/catalog")
        obj_name = cat[0]["technical_name"] if cat and "technical_name" in cat[0] else "ZSAM_SO01"
        status, details = self._request("GET", f"/api/discovery/object/{obj_name}")
        self.assertEqual(status, 200)
        self.assertIn("technical_name", details)

    # -------------------------------------------------------------
    # 5. Screen 5: End-to-End Lineage Explorer
    # -------------------------------------------------------------
    def test_05_screen_lineage_api(self):
        status, data = self._request("GET", "/api/discovery/lineage")
        self.assertEqual(status, 200)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)

    # -------------------------------------------------------------
    # 6. Screen 6: Modernization Assessment & Risk
    # -------------------------------------------------------------
    def test_06_screen_assessment_api(self):
        status, data = self._request("GET", "/api/assessment/summary")
        self.assertEqual(status, 200)
        self.assertIn("total_assessed", data)

        status, assess_obj = self._request("POST", "/api/assess", {"objectName": "ZSAM_SO01"})
        self.assertEqual(status, 200)
        self.assertIn("recommendedRoute", assess_obj)

    # -------------------------------------------------------------
    # 7. Screen 7: Target Route Compatibility Matrix
    # -------------------------------------------------------------
    def test_07_screen_target_matrix_api(self):
        status, data = self._request("GET", "/api/intelligence/landscape")
        self.assertEqual(status, 200)
        self.assertIn("route_distribution", data)
        self.assertIn("total_objects", data)

    # -------------------------------------------------------------
    # 8. Screen 8: Migration Wave Planning
    # -------------------------------------------------------------
    def test_08_screen_planning_api(self):
        status, projects = self._request("GET", "/api/planning/projects")
        self.assertEqual(status, 200)
        self.assertIsInstance(projects, list)

        status, new_proj = self._request("POST", "/api/planning/project", {
            "name": "M4.4 Test Project",
            "description": "Integration testing project",
            "targetSpace": "TEST_SPACE"
        })
        self.assertEqual(status, 200)
        self.assertIn("project_id", new_proj)

    # -------------------------------------------------------------
    # 9. Screen 9: Plan Review & Approval Workflow
    # -------------------------------------------------------------
    def test_09_screen_approval_workflow_api(self):
        # Missing planId returns 400
        status, err = self._request("POST", "/api/planning/approve", {})
        self.assertEqual(status, 400)

    # -------------------------------------------------------------
    # 10. Screen 10: Target Artifact Generation Studio
    # -------------------------------------------------------------
    def test_10_screen_generation_api(self):
        payload = {
            "objectName": "ZSAM_TEST_01",
            "targetSpace": "SALES_SPACE"
        }
        status, data = self._request("POST", "/api/generate", payload)
        self.assertEqual(status, 200)
        self.assertIn("csnPayload", data)
        self.assertIn("ddlSql", data)

    # -------------------------------------------------------------
    # 11. Screen 11: 7-Level Validation Workbench
    # -------------------------------------------------------------
    def test_11_screen_validation_workbench_api(self):
        # Missing params returns 400
        status, err = self._request("POST", "/api/validation/run", {})
        self.assertEqual(status, 400)

    # -------------------------------------------------------------
    # 12. Screen 12: Delivery Packaging & Runbooks
    # -------------------------------------------------------------
    def test_12_screen_packaging_and_runbook_api(self):
        status, rb = self._request("GET", "/api/runbook/plan-synth-test")
        self.assertEqual(status, 200)
        self.assertIn("markdown_content", rb)
        self.assertEqual(len(rb["phases"]), 5)

    # -------------------------------------------------------------
    # 13. Security Enforcement
    # -------------------------------------------------------------
    def test_13_unauthorized_request_rejected(self):
        status, err = self._request("GET", "/api/overview", api_key=None)
        self.assertEqual(status, 401)

        status, err2 = self._request("GET", "/api/overview", api_key="INVALID-KEY")
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
