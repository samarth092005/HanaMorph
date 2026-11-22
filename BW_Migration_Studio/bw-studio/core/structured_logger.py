"""
HANAMORPH BW Migration & Modernization Studio
Structured JSON Logger & Observability Engine
Milestone M5
"""

import json
import time
import sys
import os
import re
from typing import Dict, Any, Optional

class StructuredLogger:
    """
    Emits structured JSON logs with correlation IDs, component tags,
    and automatic redaction of sensitive credentials.
    """

    SECRET_KEYS = {"password", "secret", "token", "apikey", "api_key", "authorization", "cookie"}
    CREDENTIAL_REGEX = re.compile(r"(password|secret|bearer|token)\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?", re.IGNORECASE)

    def __init__(self, component: str = "CORE", stream=sys.stdout):
        self.component = component
        self.stream = stream

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = {}
        for k, v in data.items():
            if any(s in k.lower() for s in self.SECRET_KEYS):
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, dict):
                cleaned[k] = self._redact_dict(v)
            elif isinstance(v, str):
                cleaned[k] = self._redact_string(v)
            else:
                cleaned[k] = v
        return cleaned

    def _redact_string(self, msg: str) -> str:
        return self.CREDENTIAL_REGEX.sub(r"\1=[REDACTED]", msg)

    def log(self, level: str, message: str, trace_id: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level.upper(),
            "component": self.component,
            "message": self._redact_string(message),
            "trace_id": trace_id or "trace-default"
        }
        if extra:
            record["extra"] = self._redact_dict(extra)

        line = json.dumps(record)
        self.stream.write(line + "\n")
        self.stream.flush()

    def info(self, message: str, trace_id: Optional[str] = None, **extra):
        self.log("INFO", message, trace_id=trace_id, extra=extra)

    def warn(self, message: str, trace_id: Optional[str] = None, **extra):
        self.log("WARN", message, trace_id=trace_id, extra=extra)

    def error(self, message: str, trace_id: Optional[str] = None, **extra):
        self.log("ERROR", message, trace_id=trace_id, extra=extra)

    def debug(self, message: str, trace_id: Optional[str] = None, **extra):
        self.log("DEBUG", message, trace_id=trace_id, extra=extra)
