import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from connectors.credential_vault import CredentialVault
from connectors.base_connection_manager import ConnectionStatus
from connectors.bw_connection_manager import BWConnectionManager, SecurityViolationError
from connectors.datasphere_connection_manager import DatasphereConnectionManager
from connectors.btp_connection_manager import BTPConnectionManager
from connectors.hana_connection_manager import HANAConnectionManager
from connectors.cloud_foundry_connection_manager import CloudFoundryConnectionManager
from connectors.connection_hub import ConnectionHub

class TestConnectionManagers(unittest.TestCase):
    def test_credential_vault_encryption(self):
        vault = CredentialVault()
        secret = "SuperSecretPassword123"
        enc = vault.encrypt(secret)
        self.assertNotEqual(secret, enc)
        dec = vault.decrypt(enc)
        self.assertEqual(secret, dec)

    def test_credential_masking(self):
        self.assertEqual(CredentialVault.mask_secret("password123"), "pa*******23")
        self.assertEqual(CredentialVault.mask_secret("abc"), "********")
        self.assertEqual(CredentialVault.mask_secret(""), "NOT_CONFIGURED")

    def test_bw_safety_guardrails(self):
        mgr = BWConnectionManager({"SAP_BW_HOST": "192.168.1.55", "SAP_BW_USER": "test"})
        with self.assertRaises(SecurityViolationError):
            mgr.execute_sap_http("POST", "/sap/bc/adt/ddic/structures")
        with self.assertRaises(SecurityViolationError):
            mgr.execute_sap_http("DELETE", "/sap/bc/adt/repository/nodestructure")
        with self.assertRaises(SecurityViolationError):
            mgr.execute_sap_http("GET", "/sap/bc/adt/cts/transports")

    def test_datasphere_oauth_distinction(self):
        # Configure only interactive user
        cfg = {"DATASPHERE_HOST": "test.datasphere.cloud.sap", "DATASPHERE_USER": "varad.k@abhiyantatech.com", "DATASPHERE_PASSWORD": "123"}
        mgr = DatasphereConnectionManager(cfg)
        res = mgr.test_connection()
        self.assertEqual(res["status"], ConnectionStatus.PARTIALLY_CONFIGURED)
        self.assertIn("OAuth 2.0 Client credentials", res["message"])

    def test_btp_service_key_preference(self):
        # Interactive user without service key
        cfg = {"BTP_SUBACCOUNT_ID": "12345", "BTP_USER": "varad.k@abhiyantatech.com", "BTP_PASSWORD": "123"}
        mgr = BTPConnectionManager(cfg)
        res = mgr.test_connection()
        self.assertEqual(res["status"], ConnectionStatus.PARTIALLY_CONFIGURED)
        self.assertIn("Service Key", res["message"])

    def test_hana_read_only_invariants(self):
        cfg = {"HANA_CLOUD_HOST": "hana.ondemand.com", "HANA_CLOUD_USER": "DBADMIN", "HANA_CLOUD_PASSWORD": "HanaPassword123"}
        mgr = HANAConnectionManager(cfg)
        status = mgr.get_sanitized_status()
        self.assertTrue(status["config_summary"]["read_only_enforced"])
        self.assertEqual(status["config_summary"]["password_masked"], "Ha***********23")

    def test_hub_sanitized_status_no_passwords(self):
        hub = ConnectionHub.get_instance()
        statuses = hub.get_all_statuses()
        self.assertEqual(len(statuses), 5)
        for s in statuses:
            json_str = str(s)
            self.assertNotIn("Tonystark@2019", json_str)
            self.assertNotIn("pass@123", json_str)

if __name__ == "__main__":
    unittest.main()
