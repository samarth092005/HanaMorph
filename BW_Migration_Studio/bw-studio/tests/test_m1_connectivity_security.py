"""
Unit Tests for Connection Security Boundaries & Benign RFC Diagnostics
Milestone M1.5 Verification
"""

import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from connectors.bw_connection_manager import BWConnectionManager, SecurityViolationError
from connectors.mock_rfc import MockRFCClient

class TestConnectivitySecurity(unittest.TestCase):

    def setUp(self):
        self.config = {
            "SAP_BW_HOST": "192.168.1.55",
            "SAP_BW_CLIENT": "200",
            "SAP_BW_USER": "int_samarth",
            "SAP_BW_PASSWORD": "SuperSecretPassword123!",
            "SAP_BW_HTTP_PORT": "8000",
            "SAP_BW_RFC_PORT": "3300",
            "SAP_BW_USE_HTTPS": "false"
        }
        self.mgr = BWConnectionManager(self.config)

    def test_http_mutating_verbs_strictly_blocked(self):
        for verb in ["POST", "PUT", "DELETE", "PATCH", "TRACE"]:
            with self.subTest(verb=verb):
                with self.assertRaises(SecurityViolationError) as ctx:
                    self.mgr.execute_sap_http(verb, "/sap/bc/adt/discovery")
                self.assertIn("forbidden", str(ctx.exception).lower())

    def test_forbidden_sap_endpoints_blocked(self):
        forbidden_paths = [
            "/sap/bc/adt/cts/transports",
            "/sap/bc/adt/activation/activate",
            "/sap/bc/adt/ddic/tables/create",
            "/sap/bc/adt/repository/lock",
            "/sap/opu/odata/delete_service"
        ]
        for path in forbidden_paths:
            with self.subTest(path=path):
                with self.assertRaises(SecurityViolationError) as ctx:
                    self.mgr.execute_sap_http("GET", path)
                self.assertIn("zero-modification policy", str(ctx.exception).lower())

    def test_credential_sanitization_in_status_and_errors(self):
        status = self.mgr.get_sanitized_status()
        self.assertNotIn("SuperSecretPassword123!", str(status))
        self.assertTrue(status["config_summary"]["password_configured"])
        self.assertIn("****", status["config_summary"]["password_masked"])

    def test_benign_rfc_diagnostics_succeed(self):
        mock_client = MockRFCClient(sys_id="S21", client="200")
        
        # Test RFC_PING
        res_ping = self.mgr.execute_benign_rfc("RFC_PING", rfc_client=mock_client)
        self.assertEqual(res_ping["status"], "SUCCESS")
        self.assertEqual(res_ping["function"], "RFC_PING")
        self.assertTrue(res_ping["read_only_verified"])

        # Test STFC_CONNECTION
        res_echo = self.mgr.execute_benign_rfc(
            "STFC_CONNECTION",
            params={"REQUTEXT": "HanaMorph Diagnostic Handshake"},
            rfc_client=mock_client
        )
        self.assertEqual(res_echo["status"], "SUCCESS")
        self.assertEqual(res_echo["result"]["ECHOTEXT"], "HanaMorph Diagnostic Handshake")
        self.assertIn("S21", res_echo["result"]["RESPTEXT"])

    def test_unapproved_rfcs_strictly_blocked(self):
        mock_client = MockRFCClient(sys_id="S21", client="200")
        unapproved = [
            "RFC_READ_TABLE",
            "BAPI_USER_GET_DETAIL",
            "TRINT_CREATE_TR",
            "RS_DTP_ACTIVATE",
            "BAPI_TRANSACTION_COMMIT",
            "RFC_ABAP_INSTALL_AND_RUN"
        ]
        for func in unapproved:
            with self.subTest(func=func):
                with self.assertRaises(SecurityViolationError) as ctx:
                    self.mgr.execute_benign_rfc(func, rfc_client=mock_client)
                self.assertIn("forbidden", str(ctx.exception).lower())

if __name__ == "__main__":
    unittest.main()
