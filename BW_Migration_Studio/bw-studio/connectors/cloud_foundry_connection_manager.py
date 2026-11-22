import urllib.request
import urllib.parse
import urllib.error
import json
import time
import os
from .base_connection_manager import BaseConnectionManager, ConnectionStatus
from .credential_vault import CredentialVault

class CloudFoundryConnectionManager(BaseConnectionManager):
    """
    Cloud Foundry Connection Manager for SAP BTP.
    Manages API endpoint, Org, Space, and CLI/API authentication.
    """
    def __init__(self, config: dict):
        super().__init__("cloud_foundry", "Cloud Foundry (BTP Runtime)", config)
        self.api_endpoint = self.config.get("CF_API_ENDPOINT", "").strip()
        self.org = self.config.get("CF_ORG", "").strip()
        self.space = self.config.get("CF_SPACE", "").strip()
        self.auth_type = self.config.get("CF_AUTH_TYPE", "SERVICE_KEY").strip()
        self.service_key_path = self.config.get("CF_SERVICE_KEY_PATH", "").strip()
        self.client_id = self.config.get("CF_CLIENT_ID", "").strip()
        self.client_secret = self.config.get("CF_CLIENT_SECRET", "").strip()
        self.user = self.config.get("CF_USER", "").strip()
        self.password = self.config.get("CF_PASSWORD", "").strip()

    def test_connection(self) -> dict:
        self.last_checked = time.strftime("%Y-%m-%d %H:%M:%S")

        if not self.api_endpoint:
            self.status = ConnectionStatus.NOT_CONFIGURED
            self.details = {
                "api_endpoint": "NOT_CONFIGURED",
                "org": self.org or "NOT_CONFIGURED",
                "space": self.space or "NOT_CONFIGURED",
                "interactive_user": self.user or "NOT_CONFIGURED",
                "action_required": "Provide CF_API_ENDPOINT (e.g. https://api.cf.eu10.hana.ondemand.com) in .env"
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": 0.0,
                "message": "Cloud Foundry API endpoint is not configured in local .env",
                "details": self.details
            }

        start_time = time.perf_counter()
        info_url = self.api_endpoint.rstrip("/") + "/v3/info"
        try:
            req = urllib.request.Request(info_url, headers={"User-Agent": "HanaMorph-BW-Studio/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                self.latency_ms = (time.perf_counter() - start_time) * 1000.0

                cli_min = data.get("min_cli_version", "N/A")
                desc = data.get("description", "Cloud Foundry on SAP BTP")

                self.status = ConnectionStatus.CONNECTED
                self.details = {
                    "api_endpoint": self.api_endpoint,
                    "description": desc,
                    "org": self.org,
                    "space": self.space,
                    "min_cli_version": cli_min,
                    "endpoint_healthy": True
                }
                return {
                    "system_id": self.system_id,
                    "status": self.status,
                    "success": True,
                    "latency_ms": self.latency_ms,
                    "message": "Cloud Foundry API endpoint reached and validated.",
                    "details": self.details
                }
        except Exception as e:
            self.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.status = ConnectionStatus.FAILED
            self.last_error = f"Cannot reach Cloud Foundry at {info_url}: {e}"
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": self.latency_ms,
                "message": self.last_error,
                "details": {"api_endpoint": self.api_endpoint}
            }

    def get_sanitized_status(self) -> dict:
        return {
            "system_id": self.system_id,
            "display_name": self.display_name,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "last_checked": self.last_checked,
            "last_error": self.last_error,
            "config_summary": {
                "api_endpoint": self.api_endpoint or "NOT_CONFIGURED",
                "org": self.org or "NOT_CONFIGURED",
                "space": self.space or "NOT_CONFIGURED",
                "interactive_user": self.user or "NOT_CONFIGURED",
                "interactive_password_masked": CredentialVault.mask_secret(self.password),
                "auth_type": self.auth_type
            },
            "details": self.details
        }
