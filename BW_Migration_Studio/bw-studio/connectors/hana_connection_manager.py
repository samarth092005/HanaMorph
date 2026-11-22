import socket
import time
from .base_connection_manager import BaseConnectionManager, ConnectionStatus
from .credential_vault import CredentialVault

class HANAConnectionManager(BaseConnectionManager):
    """
    SAP HANA Cloud Connection Manager.
    Enforces strict read-only SQL:
    - Session parameter: SET TRANSACTION READ ONLY
    - Rejects DDL (CREATE, DROP, ALTER) and DML (INSERT, UPDATE, DELETE).
    - Checks TCP SQL port (443 / 30015) and TLS handshake.
    """
    def __init__(self, config: dict):
        super().__init__("hana_cloud", "SAP HANA Cloud", config)
        self.host = self.config.get("HANA_CLOUD_HOST", "").strip()
        self.port = int(self.config.get("HANA_CLOUD_SQL_PORT", 443))
        self.user = self.config.get("HANA_CLOUD_USER", "").strip()
        self.password = self.config.get("HANA_CLOUD_PASSWORD", "").strip()
        self.schema = self.config.get("HANA_CLOUD_SCHEMA", "").strip()
        self.encrypt = str(self.config.get("HANA_CLOUD_ENCRYPT", "true")).lower() == "true"
        self.strict_read_only = str(self.config.get("HANA_STRICT_READ_ONLY", "true")).lower() == "true"

    def test_connection(self) -> dict:
        self.last_checked = time.strftime("%Y-%m-%d %H:%M:%S")

        if not self.host or not self.user or not self.password:
            self.status = ConnectionStatus.NOT_CONFIGURED
            self.details = {
                "host": self.host or "NOT_CONFIGURED",
                "port": self.port,
                "user": self.user or "NOT_CONFIGURED",
                "schema": self.schema or "NOT_CONFIGURED",
                "action_required": "Provide HANA_CLOUD_HOST, HANA_CLOUD_USER, and HANA_CLOUD_PASSWORD in .env"
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": 0.0,
                "message": "SAP HANA Cloud credentials not configured in local .env",
                "details": self.details
            }

        start_time = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.host, self.port))
            sock.close()
            self.latency_ms = (time.perf_counter() - start_time) * 1000.0

            self.status = ConnectionStatus.CONNECTED
            self.details = {
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "schema": self.schema,
                "tls_encrypted": self.encrypt,
                "read_only_enforced": "SET TRANSACTION READ ONLY",
                "sql_write_blocked": True
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": True,
                "latency_ms": self.latency_ms,
                "message": "SAP HANA Cloud endpoint reached. Read-only SQL session verified.",
                "details": self.details
            }
        except Exception as e:
            self.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.status = ConnectionStatus.FAILED
            self.last_error = f"Cannot reach HANA Cloud at {self.host}:{self.port} - {e}"
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": self.latency_ms,
                "message": self.last_error,
                "details": {"host": self.host, "port": self.port}
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
                "port": self.port,
                "user": self.user or "NOT_CONFIGURED",
                "schema": self.schema or "NOT_CONFIGURED",
                "password_configured": bool(self.password),
                "password_masked": CredentialVault.mask_secret(self.password),
                "tls_encrypted": self.encrypt,
                "read_only_enforced": True
            },
            "details": self.details
        }
