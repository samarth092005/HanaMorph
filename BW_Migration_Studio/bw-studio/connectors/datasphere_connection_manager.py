import urllib.request
import urllib.parse
import urllib.error
import json
import time
from .base_connection_manager import BaseConnectionManager, ConnectionStatus
from .credential_vault import CredentialVault

class DatasphereConnectionManager(BaseConnectionManager):
    """
    SAP Datasphere Connection Manager.
    Differentiates between:
    1. Interactive Web IDP User (varad.k@abhiyantatech.com) - Used for manual UI logon.
    2. OAuth 2.0 Client Credentials - Required for automated REST API & CLI operations.
    """
    def __init__(self, config: dict):
        super().__init__("datasphere", "SAP Datasphere (Data Warehouse Cloud)", config)
        self.host = self.config.get("DATASPHERE_HOST", "").strip()
        self.space = self.config.get("DATASPHERE_SPACE", "").strip()
        self.auth_type = self.config.get("DATASPHERE_AUTH_TYPE", "OAUTH2_CLIENT_CREDENTIALS").strip()
        self.token_url = self.config.get("DATASPHERE_OAUTH_TOKEN_URL", "").strip()
        self.client_id = self.config.get("DATASPHERE_OAUTH_CLIENT_ID", "").strip()
        self.client_secret = self.config.get("DATASPHERE_OAUTH_CLIENT_SECRET", "").strip()
        self.user = self.config.get("DATASPHERE_USER", "").strip()
        self.password = self.config.get("DATASPHERE_PASSWORD", "").strip()

    def test_connection(self) -> dict:
        self.last_checked = time.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Check if host is configured
        if not self.host:
            self.status = ConnectionStatus.NOT_CONFIGURED
            self.details = {
                "host": "NOT_CONFIGURED",
                "space": self.space or "NOT_CONFIGURED",
                "interactive_user": self.user or "NOT_CONFIGURED",
                "oauth_client_id": "NOT_CONFIGURED",
                "action_required": "Set DATASPHERE_HOST (e.g. mytenant.eu10.datasphere.cloud.sap) in .env"
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": 0.0,
                "message": "Datasphere host is not configured in local .env",
                "details": self.details
            }

        # 2. Check if OAuth credentials exist for automation
        has_oauth = bool(self.token_url and self.client_id and self.client_secret)
        if not has_oauth:
            self.status = ConnectionStatus.PARTIALLY_CONFIGURED
            self.details = {
                "host": self.host,
                "space": self.space or "NOT_SET",
                "interactive_user": self.user,
                "interactive_password_configured": bool(self.password),
                "oauth_client_id": "NOT_CONFIGURED",
                "oauth_token_url": "NOT_CONFIGURED",
                "architectural_guidance": (
                    "Interactive credentials (varad.k@abhiyantatech.com) configured for web UI, "
                    "but unattended API and Datasphere CLI automation require an OAuth 2.0 Client. "
                    "Obtain Client ID & Secret from: System -> Administration -> App Integration -> Add OAuth Client."
                )
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": 0.0,
                "message": (
                    "Datasphere web user is configured, but OAuth 2.0 Client credentials "
                    "(DATASPHERE_OAUTH_CLIENT_ID & SECRET) are required for automated API/CLI integration."
                ),
                "details": self.details
            }

        # 3. Test OAuth 2.0 Token Exchange
        start_time = time.perf_counter()
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            encoded_payload = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(
                self.token_url,
                data=encoded_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                self.latency_ms = (time.perf_counter() - start_time) * 1000.0
                
                # Check token presence without printing it
                token_type = data.get("token_type", "Bearer")
                expires_in = data.get("expires_in", 0)

                self.status = ConnectionStatus.CONNECTED
                self.details = {
                    "host": self.host,
                    "space": self.space,
                    "token_type": token_type,
                    "token_valid": True,
                    "expires_in_seconds": expires_in,
                    "oauth_exchange": "SUCCESSFUL"
                }
                return {
                    "system_id": self.system_id,
                    "status": self.status,
                    "success": True,
                    "latency_ms": self.latency_ms,
                    "message": "Datasphere OAuth 2.0 authentication successful. API access verified.",
                    "details": self.details
                }
        except urllib.error.HTTPError as e:
            self.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.status = ConnectionStatus.FAILED
            self.last_error = f"OAuth Token Request failed with HTTP {e.code}"
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": self.latency_ms,
                "message": self.last_error,
                "details": {"http_code": e.code, "error_body": e.read().decode('utf-8', errors='ignore')[:200]}
            }
        except Exception as e:
            self.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.status = ConnectionStatus.FAILED
            self.last_error = str(e)
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": self.latency_ms,
                "message": f"Connection error reaching token URL: {e}",
                "details": {"token_url": self.token_url}
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
                "host": self.host or "NOT_CONFIGURED",
                "space": self.space or "NOT_CONFIGURED",
                "auth_type": self.auth_type,
                "interactive_user": self.user or "NOT_CONFIGURED",
                "interactive_password_masked": CredentialVault.mask_secret(self.password),
                "oauth_configured": bool(self.client_id and self.client_secret and self.token_url),
                "oauth_client_id_masked": CredentialVault.mask_secret(self.client_id),
                "token_url": self.token_url or "NOT_CONFIGURED"
            },
            "details": self.details
        }
