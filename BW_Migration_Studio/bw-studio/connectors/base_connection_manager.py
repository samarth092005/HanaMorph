import time
from abc import ABC, abstractmethod

class ConnectionStatus:
    NOT_CONFIGURED = "NOT CONFIGURED"
    PARTIALLY_CONFIGURED = "PARTIALLY CONFIGURED"
    CONFIGURED = "CONFIGURED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    FAILED = "FAILED"
    READ_ONLY_ENFORCED = "READ ONLY ENFORCED"

class BaseConnectionManager(ABC):
    """
    Abstract base connection manager.
    Enforces standardized status reporting, latency tracking, read-only safety,
    and guaranteed zero credential leakage.
    """
    def __init__(self, system_id: str, display_name: str, config: dict):
        self.system_id = system_id
        self.display_name = display_name
        self.config = config or {}
        self.status = ConnectionStatus.NOT_CONFIGURED
        self.latency_ms = 0.0
        self.last_checked = None
        self.last_error = None
        self.details = {}
        self.read_only_enforced = True

    @abstractmethod
    def test_connection(self) -> dict:
        """
        Executes a safe, read-only connectivity test.
        Must return a structured dictionary with keys:
        - status: str (from ConnectionStatus)
        - success: bool
        - latency_ms: float
        - message: str
        - details: dict (sanitized)
        """
        pass

    @abstractmethod
    def get_sanitized_status(self) -> dict:
        """
        Returns a completely sanitized status representation suitable for
        public UI or logging, with all passwords/secrets masked or omitted.
        """
        pass
