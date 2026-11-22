import os
from .credential_vault import CredentialVault
from .bw_connection_manager import BWConnectionManager
from .datasphere_connection_manager import DatasphereConnectionManager
from .btp_connection_manager import BTPConnectionManager
from .hana_connection_manager import HANAConnectionManager
from .cloud_foundry_connection_manager import CloudFoundryConnectionManager

class ConnectionHub:
    """
    Central Connection Registry and Orchestrator for all 5 enterprise target environments:
    1. SAP BW S21 (AS ABAP & BW)
    2. SAP Datasphere
    3. SAP BTP
    4. SAP HANA Cloud
    5. Cloud Foundry
    """
    _instance = None

    @classmethod
    def get_instance(cls, env_path=None):
        if cls._instance is None:
            cls._instance = ConnectionHub(env_path)
        return cls._instance

    def __init__(self, env_path=None):
        self.vault = CredentialVault()
        self.config = self.vault.load_env_file(env_path)

        self.managers = {
            "bw_s21": BWConnectionManager(self.config),
            "datasphere": DatasphereConnectionManager(self.config),
            "btp": BTPConnectionManager(self.config),
            "hana_cloud": HANAConnectionManager(self.config),
            "cloud_foundry": CloudFoundryConnectionManager(self.config)
        }

    def reload_config(self, env_path=None):
        self.config = self.vault.load_env_file(env_path)
        self.managers["bw_s21"] = BWConnectionManager(self.config)
        self.managers["datasphere"] = DatasphereConnectionManager(self.config)
        self.managers["btp"] = BTPConnectionManager(self.config)
        self.managers["hana_cloud"] = HANAConnectionManager(self.config)
        self.managers["cloud_foundry"] = CloudFoundryConnectionManager(self.config)

    def get_all_statuses(self) -> list:
        return [mgr.get_sanitized_status() for mgr in self.managers.values()]

    def test_connection(self, system_id: str) -> dict:
        mgr = self.managers.get(system_id)
        if not mgr:
            return {
                "system_id": system_id,
                "status": "NOT_FOUND",
                "success": False,
                "latency_ms": 0.0,
                "message": f"Unknown system ID: {system_id}"
            }
        return mgr.test_connection()

    def test_all(self) -> dict:
        results = {}
        for sys_id, mgr in self.managers.items():
            results[sys_id] = mgr.test_connection()
        return results
