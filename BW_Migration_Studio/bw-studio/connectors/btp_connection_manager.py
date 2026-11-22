import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from .base_connection_manager import BaseConnectionManager, ConnectionStatus
from .credential_vault import CredentialVault

class BTPConnectionManager(BaseConnectionManager):
    """
    SAP BTP (Business Technology Platform) Connection Manager.
    Enforces enterprise best practice:
    - Rejects personal interactive passwords for unattended automation.
    - Requires Service Keys (JSON) or OAuth2 Client Credentials from BTP subaccount.
    """
    def __init__(self, config: dict):
        super().__init__("btp", "SAP BTP (Business Technology Platform)", config)
        self.subaccount_id = self.config.get("BTP_SUBACCOUNT_ID", "").strip()
        self.region = self.config.get("BTP_REGION", "eu10").strip()
        self.auth_type = self.config.get("BTP_AUTH_TYPE", "SERVICE_KEY").strip()
        self.service_key_path = self.config.get("BTP_SERVICE_KEY_PATH", "").strip()
        self.oauth_url = self.config.get("BTP_OAUTH_URL", "").strip()
        self.client_id = self.config.get("BTP_CLIENT_ID", "").strip()
        self.client_secret = self.config.get("BTP_CLIENT_SECRET", "").strip()
        self.user = self.config.get("BTP_USER", "").strip()
        self.password = self.config.get("BTP_PASSWORD", "").strip()

    def test_connection(self) -> dict:
        self.last_checked = time.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Check if subaccount is configured
        if not self.subaccount_id and not self.oauth_url and not os.path.exists(self.service_key_path):
            self.status = ConnectionStatus.NOT_CONFIGURED
            self.details = {
                "subaccount_id": "NOT_CONFIGURED",
                "region": self.region,
                "interactive_user": self.user or "NOT_CONFIGURED",
                "service_key": "NOT_FOUND",
                "action_required": "Provide BTP_SUBACCOUNT_ID and a Service Key JSON in .env"
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": 0.0,
                "message": "SAP BTP Subaccount / Service Key is not configured in local .env",
                "details": self.details
            }

        # 2. Check service key vs interactive user
        has_service_key = bool(self.service_key_path and os.path.exists(self.service_key_path))
        has_oauth = bool(self.oauth_url and self.client_id and self.client_secret)

        if not has_service_key and not has_oauth:
            self.status = ConnectionStatus.PARTIALLY_CONFIGURED
            self.details = {
                "subaccount_id": self.subaccount_id or "NOT_SET",
                "region": self.region,
                "interactive_user": self.user,
                "interactive_password_configured": bool(self.password),
                "service_key_present": False,
                "security_guidance": (
                    "Personal BTP passwords (varad.k@abhiyantatech.com) are rejected for unattended automation. "
                    "Create an instance and Service Key in BTP (e.g. Destination Service or Authorization & Trust Management) "
                    "and place the JSON at secrets/btp-service-key.json."
                )
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": 0.0,
                "message": (
                    "Interactive user is configured, but BTP automation requires a Service Key or OAuth Client "
                    "to prevent MFA failures and session expirations."
                ),
                "details": self.details
            }

        # 3. Test Service Key / OAuth exchange
        start_time = time.perf_counter()
        token_url = self.oauth_url
        c_id = self.client_id
        c_secret = self.client_secret

        if has_service_key:
            try:
                with open(self.service_key_path, "r", encoding="utf-8") as f:
                    sk = json.load(f)
                    uaa = sk.get("uaa", {})
                    token_url = uaa.get("url", "") + "/oauth/token"
                    c_id = uaa.get("clientid", "")
                    c_secret = uaa.get("clientsecret", "")
            except Exception as e:
                self.status = ConnectionStatus.FAILED
                self.last_error = f"Invalid service key file: {e}"
                return {
                    "system_id": self.system_id,
                    "status": self.status,
                    "success": False,
                    "latency_ms": 0.0,
                    "message": self.last_error,
                    "details": {"path": self.service_key_path}
                }

        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": c_id,
                "client_secret": c_secret
            }
            encoded_payload = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(
                token_url,
                data=encoded_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                self.latency_ms = (time.perf_counter() - start_time) * 1000.0

                self.status = ConnectionStatus.CONNECTED
                self.details = {
                    "subaccount_id": self.subaccount_id,
                    "region": self.region,
                    "auth_method": "SERVICE_KEY" if has_service_key else "OAUTH2_CLIENT",
                    "token_valid": True,
                    "expires_in_seconds": data.get("expires_in", 0)
                }
                return {
                    "system_id": self.system_id,
                    "status": self.status,
                    "success": True,
                    "latency_ms": self.latency_ms,
                    "message": "SAP BTP Service Key authentication successful.",
                    "details": self.details
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
                "message": f"BTP Token exchange failed: {e}",
                "details": {"token_url": token_url}
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
                "subaccount_id": self.subaccount_id or "NOT_CONFIGURED",
                "region": self.region,
                "auth_type": self.auth_type,
                "service_key_path": self.service_key_path,
                "service_key_found": bool(self.service_key_path and os.path.exists(self.service_key_path)),
                "interactive_user": self.user or "NOT_CONFIGURED",
                "oauth_configured": bool(self.client_id and self.client_secret)
            },
            "details": self.details
        }
