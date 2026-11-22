"""
HANAMORPH BW Migration & Modernization Studio
Delivery Package Integrity & Schema Validator
Milestone M4.3
"""

import os
import json
import hashlib
import re
from typing import Dict, Any, List, Optional

class PackageValidationResult:
    def __init__(
        self,
        package_dir: str,
        is_valid: bool,
        manifest_verified: bool,
        total_files_checked: int,
        corrupted_files: List[str],
        schema_errors: List[Dict[str, str]],
        security_findings: List[str],
        details: Dict[str, Any]
    ):
        self.package_dir = package_dir
        self.is_valid = is_valid
        self.manifest_verified = manifest_verified
        self.total_files_checked = total_files_checked
        self.corrupted_files = corrupted_files
        self.schema_errors = schema_errors
        self.security_findings = security_findings
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_dir": self.package_dir,
            "is_valid": self.is_valid,
            "manifest_verified": self.manifest_verified,
            "total_files_checked": self.total_files_checked,
            "corrupted_files": self.corrupted_files,
            "schema_errors": self.schema_errors,
            "security_findings": self.security_findings,
            "details": self.details
        }


class PackageValidator:
    """
    Independently verifies sealed delivery packages for:
    1. Cryptographic SHA-256 integrity against manifest.json
    2. Syntax and schema correctness (CSN 2.0, SQL DDL, Replication Flow, SAC)
    3. Strict credential leak prevention (zero passwords, keys, or tokens)
    """

    CREDENTIAL_PATTERNS = [
        re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
        re.compile(r"secret\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
        re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
        re.compile(r"apikey\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE)
    ]

    def validate_package(self, package_dir: str) -> PackageValidationResult:
        if not os.path.exists(package_dir):
            raise FileNotFoundError(f"Package directory does not exist: {package_dir}")

        manifest_path = os.path.join(package_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return PackageValidationResult(
                package_dir=package_dir,
                is_valid=False,
                manifest_verified=False,
                total_files_checked=0,
                corrupted_files=["manifest.json missing"],
                schema_errors=[],
                security_findings=[],
                details={"error": "Package does not contain manifest.json"}
            )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        files_map = manifest.get("files", {})
        total_files = len(files_map)
        corrupted_files: List[str] = []
        schema_errors: List[Dict[str, str]] = []
        security_findings: List[str] = []
        details: Dict[str, Any] = {"inspected_files": []}

        # 1. Cryptographic Hash & Tamper Verification
        for rel_path, meta in files_map.items():
            full_path = os.path.join(package_dir, rel_path)
            if not os.path.exists(full_path):
                corrupted_files.append(f"{rel_path} (file missing on disk)")
                continue

            with open(full_path, "rb") as f:
                content_bytes = f.read()

            actual_sha = hashlib.sha256(content_bytes).hexdigest()
            expected_sha = meta.get("sha256")
            if actual_sha != expected_sha:
                corrupted_files.append(f"{rel_path} (hash mismatch: expected {expected_sha}, got {actual_sha})")

            # 2. Security / Credential Leak Check
            try:
                content_str = content_bytes.decode("utf-8")
                for pattern in self.CREDENTIAL_PATTERNS:
                    if pattern.search(content_str):
                        security_findings.append(f"Potential credential leak detected in {rel_path}")
                        break
            except UnicodeDecodeError:
                pass # Binary files

            # 3. Schema & Syntax Validation by File Type
            self._validate_file_schema(rel_path, content_bytes, schema_errors)
            details["inspected_files"].append(rel_path)

        manifest_verified = (len(corrupted_files) == 0)
        is_valid = manifest_verified and (len(schema_errors) == 0) and (len(security_findings) == 0)

        return PackageValidationResult(
            package_dir=package_dir,
            is_valid=is_valid,
            manifest_verified=manifest_verified,
            total_files_checked=total_files,
            corrupted_files=corrupted_files,
            schema_errors=schema_errors,
            security_findings=security_findings,
            details=details
        )

    def _validate_file_schema(self, rel_path: str, content: bytes, errors: List[Dict[str, str]]):
        fname = os.path.basename(rel_path)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return

        # A. CSN Schema Check (*.csn.json)
        if fname.endswith(".csn.json"):
            try:
                data = json.loads(text)
                if "$schema" not in data or "definitions" not in data:
                    errors.append({"file": rel_path, "error": "Missing required CSN keys ($schema, definitions)"})
            except Exception as e:
                errors.append({"file": rel_path, "error": f"Invalid JSON syntax: {str(e)}"})

        # B. Replication Flow Check (*_repl_flow.json)
        elif fname.endswith("_repl_flow.json"):
            try:
                data = json.loads(text)
                req_keys = ["flow_id", "source", "target", "replication_settings", "mappings"]
                for k in req_keys:
                    if k not in data:
                        errors.append({"file": rel_path, "error": f"Replication Flow missing key: {k}"})
            except Exception as e:
                errors.append({"file": rel_path, "error": f"Invalid Replication Flow JSON: {str(e)}"})

        # C. SAC Analytic Model Check (SAC_*_model.json)
        elif fname.startswith("SAC_") and fname.endswith(".json"):
            try:
                data = json.loads(text)
                req_keys = ["model_id", "dimensions", "measures", "data_source"]
                for k in req_keys:
                    if k not in data:
                        errors.append({"file": rel_path, "error": f"SAC Model missing key: {k}"})
            except Exception as e:
                errors.append({"file": rel_path, "error": f"Invalid SAC Model JSON: {str(e)}"})

        # D. SQL DDL Check (*.sql)
        elif fname.endswith(".sql"):
            upper_sql = text.strip().upper()
            if not (upper_sql.startswith("CREATE") or upper_sql.startswith("--")):
                errors.append({"file": rel_path, "error": "SQL file does not begin with standard DDL (CREATE ...)"})
