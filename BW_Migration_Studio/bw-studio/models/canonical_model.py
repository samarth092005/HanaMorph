"""
HANAMORPH BW Migration & Modernization Studio
Canonical Metadata Model and URN Identity Engine
Milestone M1.2
"""

import json
import hashlib
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union

class CanonicalURN:
    """
    Standardized, collision-proof Uniform Resource Name (URN) for SAP BW metadata.
    Format:
        Versioned: urn:sap:bw:<system>:<client>:<type>:<escaped_name>:<version>
        Stable:    urn:sap:bw:<system>:<client>:<type>:<escaped_name>
    """
    PREFIX = "urn:sap:bw"

    def __init__(
        self,
        system_id: str,
        client: str,
        object_type: str,
        technical_name: str,
        version: Optional[str] = "A"
    ):
        self.system_id = self.normalize_system(system_id)
        self.client = self.normalize_client(client)
        self.object_type = self.normalize_type(object_type)
        self.raw_technical_name = technical_name.strip()
        self.escaped_name = self.escape_name(self.raw_technical_name)
        self.version = self.normalize_version(version)

    @staticmethod
    def normalize_system(system_id: str) -> str:
        s = (system_id or "").strip().lower()
        if not s:
            raise ValueError("system_id cannot be empty")
        return s

    @staticmethod
    def normalize_client(client: str) -> str:
        c = str(client or "").strip()
        if not c:
            return "000"
        # Zero-pad numeric client strings to 3 digits (e.g., '10' -> '010', '200' -> '200')
        if c.isdigit() and len(c) < 3:
            c = c.zfill(3)
        return c

    @staticmethod
    def normalize_type(obj_type: str) -> str:
        t = (obj_type or "").strip().lower()
        if not t:
            raise ValueError("object_type cannot be empty")
        # Standardize common aliases
        type_aliases = {
            "adso": "adso",
            "advanced_datastore": "adso",
            "hcpr": "hcpr",
            "composite_provider": "hcpr",
            "cpro": "hcpr",
            "iobj": "iobj",
            "infoobject": "iobj",
            "trfn": "trfn",
            "transformation": "trfn",
            "dtpa": "dtpa",
            "dtp": "dtpa",
            "elem": "elem",
            "query": "elem",
            "bw_query": "elem",
            "isrc": "isrc",
            "infosource": "isrc",
            "osrc": "osrc",
            "datasource": "osrc"
        }
        return type_aliases.get(t, t)

    @staticmethod
    def normalize_version(version: Optional[str]) -> str:
        if not version:
            return "A"
        v = version.strip().upper()
        # Valid SAP BW versions: A (Active), M (Modified), D (Delivery), T (Transport/Draft)
        if v not in ["A", "M", "D", "T"]:
            return v
        return v

    @staticmethod
    def escape_name(name: str) -> str:
        """
        URL percent-encodes slashes and special characters in SAP technical names
        e.g., '/COMPANY/SALES_01' -> '%2FCOMPANY%2FSALES_01'
        """
        return urllib.parse.quote(name, safe="")

    @staticmethod
    def unescape_name(escaped: str) -> str:
        return urllib.parse.unquote(escaped)

    @property
    def stable_urn(self) -> str:
        """Returns identity independent of object lifecycle version"""
        return f"{self.PREFIX}:{self.system_id}:{self.client}:{self.object_type}:{self.escaped_name}"

    @property
    def versioned_urn(self) -> str:
        """Returns full versioned URN"""
        return f"{self.stable_urn}:{self.version}"

    def __str__(self) -> str:
        return self.versioned_urn

    def __repr__(self) -> str:
        return f"CanonicalURN('{self.versioned_urn}')"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CanonicalURN):
            return self.versioned_urn == other.versioned_urn
        if isinstance(other, str):
            return self.versioned_urn == other
        return False

    def __hash__(self) -> int:
        return hash(self.versioned_urn)

    @classmethod
    def parse(cls, urn_str: str) -> "CanonicalURN":
        """
        Parses a versioned or stable canonical URN string.
        """
        if not urn_str or not urn_str.startswith(cls.PREFIX + ":"):
            raise ValueError(f"Invalid canonical URN format: '{urn_str}' (must start with '{cls.PREFIX}:')")

        parts = urn_str[len(cls.PREFIX) + 1:].split(":")
        if len(parts) < 4:
            raise ValueError(f"URN has insufficient segments: '{urn_str}'")

        system_id = parts[0]
        client = parts[1]
        obj_type = parts[2]
        escaped_name = parts[3]
        version = parts[4] if len(parts) >= 5 else "A"

        technical_name = cls.unescape_name(escaped_name)
        return cls(system_id, client, obj_type, technical_name, version)


class CanonicalField:
    """
    Represents a normalized field/attribute within a canonical BW object.
    """
    def __init__(
        self,
        field_name: str,
        data_type: str,
        position: int = 0,
        length: int = 0,
        decimals: int = 0,
        is_key: bool = False,
        aggregation: str = "NONE",
        semantics: Optional[str] = None,
        currency_unit_field: Optional[str] = None,
        compounding_parent: Optional[str] = None,
        description: Optional[str] = None
    ):
        self.field_name = field_name.strip().upper()
        self.data_type = data_type.strip().upper()
        self.position = int(position)
        self.length = int(length)
        self.decimals = int(decimals)
        self.is_key = bool(is_key)
        self.aggregation = aggregation.strip().upper()
        self.semantics = semantics.strip().upper() if semantics else None
        self.currency_unit_field = currency_unit_field.strip().upper() if currency_unit_field else None
        self.compounding_parent = compounding_parent.strip().upper() if compounding_parent else None
        self.description = description.strip() if description else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "data_type": self.data_type,
            "position": self.position,
            "length": self.length,
            "decimals": self.decimals,
            "is_key": self.is_key,
            "aggregation": self.aggregation,
            "semantics": self.semantics,
            "currency_unit_field": self.currency_unit_field,
            "compounding_parent": self.compounding_parent,
            "description": self.description
        }


class CanonicalObject:
    """
    Comprehensive Canonical Metadata Entity representing an SAP BW object.
    Includes deterministic SHA-256 content fingerprinting, provenance tracking,
    and completeness/confidence metrics.
    """
    def __init__(
        self,
        urn: Union[CanonicalURN, str],
        description: str = "",
        infoarea: str = "",
        package: str = "$TMP",
        active_status: str = "A",
        fields: Optional[List[CanonicalField]] = None,
        dependencies: Optional[List[Dict[str, str]]] = None,
        provenance: str = "LIVE_VERIFIED",
        confidence_score: float = 1.0,
        completeness_score: float = 1.0,
        extracted_at: Optional[str] = None,
        custom_attributes: Optional[Dict[str, Any]] = None
    ):
        if isinstance(urn, str):
            self.urn = CanonicalURN.parse(urn)
        else:
            self.urn = urn

        self.description = description.strip()
        self.infoarea = infoarea.strip()
        self.package = package.strip()
        self.active_status = active_status.strip().upper()
        self.fields: List[CanonicalField] = fields or []
        self.dependencies: List[Dict[str, str]] = dependencies or []
        self.provenance = provenance.strip().upper()
        self.confidence_score = max(0.0, min(1.0, float(confidence_score)))
        self.completeness_score = max(0.0, min(1.0, float(completeness_score)))
        self.extracted_at = extracted_at or datetime.now(timezone.utc).isoformat()
        self.custom_attributes = custom_attributes or {}

    @property
    def content_fingerprint(self) -> str:
        """
        Computes deterministic SHA-256 hash strictly over semantic/structural content.
        Excludes extraction timestamp so identical metadata yields identical fingerprint
        and content changes are detected even if extraction timestamp is unchanged.
        """
        canonical_payload = {
            "system_id": self.urn.system_id,
            "client": self.urn.client,
            "object_type": self.urn.object_type,
            "technical_name": self.urn.raw_technical_name,
            "version": self.urn.version,
            "description": self.description,
            "infoarea": self.infoarea,
            "package": self.package,
            "active_status": self.active_status,
            "fields": [
                f.to_dict() for f in sorted(self.fields, key=lambda x: (x.position, x.field_name))
            ],
            "dependencies": sorted(
                self.dependencies,
                key=lambda x: (x.get("source_urn", ""), x.get("target_urn", ""), x.get("dependency_type", ""))
            ),
            "custom_attributes": dict(sorted(self.custom_attributes.items()))
        }
        serialized = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_canonical_dict(self) -> Dict[str, Any]:
        """
        Produces fully serialized dictionary adhering to deterministic ordering.
        """
        return {
            "urn": self.urn.versioned_urn,
            "stable_urn": self.urn.stable_urn,
            "system_id": self.urn.system_id,
            "client": self.urn.client,
            "object_type": self.urn.object_type,
            "technical_name": self.urn.raw_technical_name,
            "version": self.urn.version,
            "description": self.description,
            "infoarea": self.infoarea,
            "package": self.package,
            "active_status": self.active_status,
            "content_fingerprint": self.content_fingerprint,
            "provenance": self.provenance,
            "confidence_score": self.confidence_score,
            "completeness_score": self.completeness_score,
            "extracted_at": self.extracted_at,
            "field_count": len(self.fields),
            "fields": [f.to_dict() for f in sorted(self.fields, key=lambda x: (x.position, x.field_name))],
            "dependencies": sorted(
                self.dependencies,
                key=lambda x: (x.get("source_urn", ""), x.get("target_urn", ""), x.get("dependency_type", ""))
            ),
            "custom_attributes": dict(sorted(self.custom_attributes.items()))
        }

    def to_json(self) -> str:
        return json.dumps(self.to_canonical_dict(), sort_keys=True, indent=2)
