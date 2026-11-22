"""
HANAMORPH BW Migration & Modernization Studio
Mock RFC Client for Benign RFC Diagnostics Testing
Milestone M1.5
"""

class MockRFCClient:
    """
    Offline Mock RFC client for verifying benign RFC diagnostic execution
    without requiring physical SAP hardware or sapnwrfc.dll.
    Supports exclusively approved benign RFC functions:
    - RFC_PING
    - STFC_CONNECTION
    """
    APPROVED_BENIGN_RFCS = {"RFC_PING", "STFC_CONNECTION"}

    def __init__(self, sys_id: str = "S21", client: str = "200"):
        self.sys_id = sys_id
        self.client = client
        self.connected = True

    def call(self, func_name: str, **kwargs) -> dict:
        func_upper = (func_name or "").strip().upper()
        if func_upper not in self.APPROVED_BENIGN_RFCS:
            raise PermissionError(
                f"[SECURITY VIOLATION] Function module '{func_upper}' is not in approved benign RFC whitelist. "
                f"Only RFC_PING and STFC_CONNECTION are permitted."
            )

        if func_upper == "RFC_PING":
            return {}

        if func_upper == "STFC_CONNECTION":
            req_text = kwargs.get("REQUTEXT", "HanaMorph Diagnostic Ping")
            return {
                "ECHOTEXT": req_text,
                "RESPTEXT": f"SAP NetWeaver AS ABAP {self.sys_id} Client {self.client} Active"
            }

        return {}

    def close(self):
        self.connected = False
