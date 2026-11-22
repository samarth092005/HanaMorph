"""
HANAMORPH BW Migration & Modernization Studio
SAP Datasphere Replication Flow Specification Generator
Milestone M4.2
"""

import json
import hashlib
from typing import Dict, Any, List, Optional

class DatasphereReplicationFlowGenerator:
    """
    Generates official SAP Datasphere Replication Flow JSON specifications.
    Supports Initial, Delta, and Real-Time CDC replication from SAP BW / S21 sources.
    """

    LOAD_TYPES = {
        "DELTA": "INITIAL_AND_DELTA",
        "INITIAL": "INITIAL_ONLY"
    }

    DELTA_METHODS = {
        "ADSO": "ODP_BW_DELTA_QUEUE",
        "INFOCUBE": "INITIAL_ONLY",
        "MASTER_DATA": "TIMESTAMP_CDC",
        "DEFAULT": "ODP_BW_DELTA_QUEUE"
    }

    def generate_replication_flow(
        self,
        space: str,
        source_object: str,
        target_name: str,
        fields: List[Dict[str, Any]],
        source_connection: str = "BW_S21_CONNECTION",
        load_type: Optional[str] = None,
        source_urn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds a complete SAP Datasphere Replication Flow specification JSON.
        """
        flow_id = f"RF_{source_object}_TO_{target_name}"
        
        # Determine load type based on object semantics
        has_keys = any(f.get("is_key") for f in fields)
        is_transactional = any(f.get("data_type") in ["CURR", "QUAN"] for f in fields)
        
        if load_type:
            determined_load = load_type
        elif is_transactional or has_keys:
            determined_load = self.LOAD_TYPES["DELTA"]
        else:
            determined_load = self.LOAD_TYPES["INITIAL"]

        delta_method = self.DELTA_METHODS["ADSO"] if determined_load == self.LOAD_TYPES["DELTA"] else "NONE"

        # Field mapping definitions
        mappings = []
        for f in fields:
            f_name = f.get("field_name", "UNKNOWN")
            mappings.append({
                "source_field": f_name,
                "target_field": f_name,
                "data_type": f.get("data_type", "CHAR"),
                "is_key": bool(f.get("is_key", False)),
                "transformation_rule": "DIRECT_MOVE"
            })

        flow_spec = {
            "$schema": "https://help.sap.com/doc/datasphere-replication-flow-v1.json",
            "flow_id": flow_id,
            "version": "1.0.0",
            "space_id": space,
            "description": f"Automated replication pipeline from SAP BW {source_object} to {target_name}",
            "source": {
                "connection_name": source_connection,
                "container_type": "ODP_BW",
                "dataset_name": source_object,
                "source_urn": source_urn or f"urn:hanamorph:bw:s21:adso:{source_object}"
            },
            "target": {
                "connection_name": "LOCAL_DATASPHERE",
                "container_type": "SPACE_LOCAL_TABLE",
                "dataset_name": target_name
            },
            "replication_settings": {
                "load_type": determined_load,
                "delta_method": delta_method,
                "truncate_target_before_load": determined_load == "INITIAL_ONLY",
                "parallel_threads": 4,
                "batch_size_rows": 50000,
                "error_handling": {
                    "max_tolerated_errors": 0,
                    "abort_on_error": True
                }
            },
            "mappings": mappings
        }

        # Compute deterministic content hash
        raw_json = json.dumps(flow_spec, sort_keys=True, indent=2)
        content_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        
        flow_spec["provenance"] = {
            "generator": "HANAMORPH_REPLICATION_FLOW_ENGINE",
            "milestone": "M4.2",
            "content_sha256": content_hash
        }

        return flow_spec
