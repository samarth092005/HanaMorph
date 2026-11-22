import urllib.request
import urllib.error
import base64
import time
import socket
from .base_connection_manager import BaseConnectionManager, ConnectionStatus
from .credential_vault import CredentialVault

class SecurityViolationError(Exception):
    pass

class BWConnectionManager(BaseConnectionManager):
    """
    SAP BW S21 Connection Manager.
    Enforces hard read-only invariants:
    - HTTP GET / HEAD only.
    - Mutating verbs (POST, PUT, DELETE, PATCH) blocked with SecurityViolationError.
    - CTS transport creation blocked.
    - DTP and process chain execution blocked.
    - Zero plain text credential logging.
    """
    def __init__(self, config: dict):
        super().__init__("bw_s21", "SAP BW S21 (NetWeaver AS ABAP)", config)
        self.host = self.config.get("SAP_BW_HOST", "").strip()
        self.client = self.config.get("SAP_BW_CLIENT", "200").strip()
        self.user = self.config.get("SAP_BW_USER", "").strip()
        self.password = self.config.get("SAP_BW_PASSWORD", "").strip()
        self.http_port = int(self.config.get("SAP_BW_HTTP_PORT", 8000))
        self.rfc_port = int(self.config.get("SAP_BW_RFC_PORT", 3300))
        self.use_https = str(self.config.get("SAP_BW_USE_HTTPS", "false")).lower() == "true"
        self.strict_read_only = str(self.config.get("SAP_BW_STRICT_READ_ONLY", "true")).lower() == "true"
        self.allow_sap_all = str(self.config.get("SAP_BW_ALLOW_SAP_ALL", "true")).lower() == "true"

    def execute_sap_http(self, method: str, endpoint: str, query_params: dict = None, headers: dict = None):
        """
        Guarded HTTP execution engine for SAP S21.
        Strictly enforces read-only safety policy.
        """
        method_upper = method.upper()
        if method_upper not in ["GET", "HEAD"]:
            raise SecurityViolationError(
                f"[SAFETY GUARDRAIL BLOCKED] Mutating HTTP method '{method_upper}' is forbidden. "
                f"S21 is restricted to strict read-only inspection."
            )

        forbidden_patterns = ["/cts/", "/transports", "/activate", "/lock", "/create", "/delete"]
        if any(p in endpoint.lower() for p in forbidden_patterns):
            raise SecurityViolationError(
                f"[SAFETY GUARDRAIL BLOCKED] Endpoint '{endpoint}' is prohibited by zero-modification policy."
            )

        protocol = "https" if self.use_https else "http"
        port = int(self.config.get("SAP_BW_HTTPS_PORT", 44300)) if self.use_https else self.http_port
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        url = f"{protocol}://{self.host}:{port}{clean_endpoint}"

        req_headers = {
            "Accept": "application/atom+xml, application/xml, text/html, */*",
            "sap-client": self.client,
            "User-Agent": "HanaMorph-BW-Studio/1.0"
        }
        if headers:
            req_headers.update(headers)

        if self.user and self.password:
            auth_str = f"{self.user}:{self.password}"
            b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('ascii')
            req_headers["Authorization"] = f"Basic {b64_auth}"

        req = urllib.request.Request(url, headers=req_headers, method=method_upper)
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                latency = (time.perf_counter() - start) * 1000.0
                return {
                    "status_code": resp.status,
                    "headers": dict(resp.headers),
                    "data": data,
                    "latency_ms": latency
                }
        except urllib.error.HTTPError as e:
            latency = (time.perf_counter() - start) * 1000.0
            return {
                "status_code": e.code,
                "headers": dict(e.headers),
                "data": e.read(),
                "latency_ms": latency
            }
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            sanitized_err = str(e).replace(self.password, "[REDACTED]") if self.password else str(e)
            raise ConnectionError(f"Network error contacting S21: {sanitized_err}")

    APPROVED_BENIGN_RFCS = {"RFC_PING", "STFC_CONNECTION"}

    def execute_benign_rfc(self, func_name: str, params: dict = None, rfc_client = None) -> dict:
        """
        Executes strictly approved benign diagnostic RFC functions (RFC_PING, STFC_CONNECTION).
        Rejects all other functions (including RFC_READ_TABLE, BAPI_USER_GET_DETAIL, CTS, etc.)
        with SecurityViolationError.
        """
        func_upper = (func_name or "").strip().upper()
        if func_upper not in self.APPROVED_BENIGN_RFCS:
            raise SecurityViolationError(
                f"[SAFETY GUARDRAIL BLOCKED] RFC Function '{func_upper}' is forbidden. "
                f"Only approved benign diagnostic functions ({', '.join(sorted(self.APPROVED_BENIGN_RFCS))}) are permitted."
            )

        start = time.perf_counter()
        if rfc_client is not None:
            # Using injected/mocked RFC client
            res = rfc_client.call(func_upper, **(params or {}))
            latency = (time.perf_counter() - start) * 1000.0
            return {
                "function": func_upper,
                "status": "SUCCESS",
                "result": res,
                "latency_ms": latency,
                "read_only_verified": True
            }

        # If live PyRFC is available
        try:
            from pyrfc import Connection
            conn_params = {
                "ashost": self.host,
                "sysnr": str(self.http_port)[-2:] if len(str(self.http_port)) >= 2 else "00",
                "client": self.client,
                "user": self.user,
                "passwd": self.password
            }
            conn = Connection(**conn_params)
            res = conn.call(func_upper, **(params or {}))
            conn.close()
            latency = (time.perf_counter() - start) * 1000.0
            return {
                "function": func_upper,
                "status": "SUCCESS",
                "result": res,
                "latency_ms": latency,
                "read_only_verified": True
            }
        except ImportError:
            return {
                "function": func_upper,
                "status": "NOT_INSTALLED",
                "result": None,
                "latency_ms": 0.0,
                "message": "PyRFC / sapnwrfc.dll not installed. RFC execution skipped in local mode."
            }
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            sanitized_err = str(e).replace(self.password, "[REDACTED]") if self.password else str(e)
            return {
                "function": func_upper,
                "status": "FAILED",
                "result": None,
                "latency_ms": latency,
                "message": sanitized_err
            }

    def test_connection(self) -> dict:
        self.last_checked = time.strftime("%Y-%m-%d %H:%M:%S")
        if not self.host or not self.user or not self.password:
            self.status = ConnectionStatus.NOT_CONFIGURED
            self.details = {
                "host": self.host or "NOT_CONFIGURED",
                "client": self.client,
                "user": self.user or "NOT_CONFIGURED",
                "auth_status": "Missing required S21 host, user, or password",
                "read_only_enforced": True
            }
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": 0.0,
                "message": "SAP BW S21 credentials not fully configured in local .env",
                "details": self.details
            }

        start_time = time.perf_counter()
        # 1. Quick TCP socket probe
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((self.host, self.http_port))
            sock.close()
        except Exception as e:
            self.status = ConnectionStatus.FAILED
            self.last_error = f"TCP Port {self.http_port} unreachable: {e}"
            self.latency_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": self.latency_ms,
                "message": self.last_error,
                "details": {"host": self.host, "port": self.http_port}
            }

        # 2. Authenticated ADT Discovery probe
        try:
            res = self.execute_sap_http("GET", "/sap/bc/adt/discovery")
            self.latency_ms = res["latency_ms"]

            if res["status_code"] == 200:
                self.status = ConnectionStatus.CONNECTED
                self.details = {
                    "host": self.host,
                    "client": self.client,
                    "user": self.user,
                    "server_type": res["headers"].get("server", "SAP NetWeaver AS ABAP"),
                    "sap_server": res["headers"].get("sap_server", "true"),
                    "endpoint_reached": "/sap/bc/adt/discovery",
                    "http_status": 200,
                    "read_only_policy": "ACTIVE (Strict GET/HEAD only)",
                    "admin_account_protected": self.allow_sap_all
                }
                return {
                    "system_id": self.system_id,
                    "status": self.status,
                    "success": True,
                    "latency_ms": self.latency_ms,
                    "message": "Authenticated ADT connection to SAP BW S21 verified successfully.",
                    "details": self.details
                }
            elif res["status_code"] == 401:
                self.status = ConnectionStatus.FAILED
                self.last_error = "HTTP 401 Unauthorized: Invalid username or password on Client " + self.client
                return {
                    "system_id": self.system_id,
                    "status": self.status,
                    "success": False,
                    "latency_ms": self.latency_ms,
                    "message": self.last_error,
                    "details": {"realm": res["headers"].get("www-authenticate", "Unknown realm")}
                }
            else:
                self.status = ConnectionStatus.FAILED
                self.last_error = f"Unexpected HTTP status {res['status_code']} from ADT discovery"
                return {
                    "system_id": self.system_id,
                    "status": self.status,
                    "success": False,
                    "latency_ms": self.latency_ms,
                    "message": self.last_error,
                    "details": {"status_code": res["status_code"]}
                }
        except Exception as e:
            self.status = ConnectionStatus.FAILED
            self.last_error = str(e)
            self.latency_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "system_id": self.system_id,
                "status": self.status,
                "success": False,
                "latency_ms": self.latency_ms,
                "message": f"ADT Discovery failed: {e}",
                "details": {"host": self.host}
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
                "client": self.client,
                "http_port": self.http_port,
                "rfc_port": self.rfc_port,
                "user": self.user or "NOT_CONFIGURED",
                "password_configured": bool(self.password),
                "password_masked": CredentialVault.mask_secret(self.password),
                "read_only_enforced": True,
                "safety_guardrails": "STRICT_READ_ONLY (POST/PUT/DELETE BLOCKED)"
            },
            "details": self.details
        }
