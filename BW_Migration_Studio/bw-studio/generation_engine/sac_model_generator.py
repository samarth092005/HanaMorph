"""
HANAMORPH BW Migration & Modernization Studio
SAP Analytics Cloud (SAC) Analytical Model Generator
Milestone M4.2
"""

import json
import hashlib
from typing import Dict, Any, List, Optional

class SACAnalyticalModelGenerator:
    """
    Generates SAP Analytics Cloud (SAC) Analytical Model metadata definitions.
    Translates BEx queries, CompositeProviders, and Datasphere Views into SAC consumption models.
    """

    DIMENSION_TYPES = {
        "DATE": "Date",
        "ORG": "Organization",
        "GENERIC": "Generic",
        "VERSION": "Version"
    }

    def generate_sac_model(
        self,
        model_name: str,
        source_object: str,
        base_view_id: str,
        fields: List[Dict[str, Any]],
        description: str = "",
        source_urn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds an SAC Analytical Model metadata specification JSON.
        """
        dimensions = []
        measures = []
        variables = []
        ambiguous_fields = []

        field_names = {f.get("field_name") for f in fields}
        cuky_field = next((f["field_name"] for f in fields if f.get("data_type") == "CUKY" or f.get("field_name") in ["CURRENCY", "WAERS"]), None)
        unit_field = next((f["field_name"] for f in fields if f.get("data_type") == "UNIT" or f.get("field_name") in ["SALES_UNIT", "MEINS", "UNIT"]), None)

        for f in fields:
            name = f.get("field_name", "UNKNOWN")
            raw_type = f.get("data_type", "CHAR").upper()
            role, defn, ambig = self._classify_field_semantics(f, cuky_field, unit_field)

            if role == "MEASURE":
                measures.append(defn)
            else:
                dimensions.append(defn)

            if ambig:
                ambiguous_fields.append(ambig)

        # Standard SAC Time Prompt Variable
        variables.append({
            "id": "VAR_FISCAL_PERIOD",
            "description": "Fiscal Year / Period Selection",
            "type": "SingleValue",
            "mandatory": False,
            "dimension": next((d["id"] for d in dimensions if d["type"] == "Date"), "CALDAY")
        })

        sac_spec = {
            "$schema": "https://help.sap.com/doc/sac-analytical-model-v1.json",
            "model_id": model_name,
            "version": "1.0.0",
            "description": description or f"SAC Analytical Consumption Model for {source_object}",
            "data_source": {
                "type": "SAP_DATASPHERE",
                "space_id": base_view_id.split(".")[0] if "." in base_view_id else "SALES_ANALYTICS",
                "artifact_name": base_view_id.split(".")[-1] if "." in base_view_id else base_view_id,
                "source_urn": source_urn or f"urn:hanamorph:bw:s21:query:{source_object}"
            },
            "dimensions": dimensions,
            "measures": measures,
            "variables": variables,
            "ambiguous_fields": ambiguous_fields,
            "settings": {
                "enable_drill_down": True,
                "cache_results": True,
                "max_result_rows": 100000
            }
        }

        raw_json = json.dumps(sac_spec, sort_keys=True, indent=2)
        content_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        sac_spec["provenance"] = {
            "generator": "HANAMORPH_SAC_MODEL_ENGINE",
            "milestone": "M4.2",
            "content_sha256": content_hash,
            "ambiguous_field_count": len(ambiguous_fields)
        }

        return sac_spec

    def _classify_field_semantics(
        self,
        f: Dict[str, Any],
        cuky_field: Optional[str],
        unit_field: Optional[str]
    ) -> tuple:
        """
        Classifies a field into MEASURE or DIMENSION using the strict priority order:
        1. Explicit source analytical semantics (role, analytics_type, AMO/QUA)
        2. Explicit aggregation metadata (SUM, AVG, MIN, MAX, COUNT)
        3. Existing validated field-role metadata (field_role)
        4. Reliable business naming/type patterns
        5. Ambiguity review flag if unconfirmed
        """
        name = f.get("field_name", "UNKNOWN").strip().upper()
        raw_type = f.get("data_type", "CHAR").strip().upper()
        decimals = int(f.get("decimals", 2))
        is_key = bool(f.get("is_key", False))
        tokens = [t for t in name.split("_") if t]

        # PRIORITY 1: Explicit Analytical Semantics
        explicit_role = (f.get("role") or f.get("analytics_type") or "").upper()
        if explicit_role == "MEASURE":
            agg = f.get("aggregation_type") or "SUM"
            return "MEASURE", self._build_measure_def(f, name, raw_type, agg, decimals, cuky_field, unit_field), None
        if explicit_role == "DIMENSION":
            return "DIMENSION", self._build_dimension_def(f, name, raw_type, is_key), None

        semantics = (f.get("semantics") or "").upper()
        if semantics == "AMO":
            agg = f.get("aggregation_type") or "SUM"
            return "MEASURE", self._build_measure_def(f, name, raw_type, agg, decimals, cuky_field, unit_field, unit_type="CURRENCY"), None
        if semantics == "QUA":
            agg = f.get("aggregation_type") or "SUM"
            return "MEASURE", self._build_measure_def(f, name, raw_type, agg, decimals, cuky_field, unit_field, unit_type="UNIT"), None
        if semantics in ["DAT", "TIM", "ID", "CODE"]:
            return "DIMENSION", self._build_dimension_def(f, name, raw_type, is_key), None

        # PRIORITY 2: Explicit Aggregation Metadata
        agg_meta = (f.get("aggregation_type") or "").upper()
        if agg_meta in ["SUM", "MAX", "MIN", "AVG", "COUNT"]:
            return "MEASURE", self._build_measure_def(f, name, raw_type, agg_meta, decimals, cuky_field, unit_field), None

        # PRIORITY 3: Existing Validated Field-Role Metadata
        field_role = (f.get("field_role") or "").upper()
        if field_role == "MEASURE":
            return "MEASURE", self._build_measure_def(f, name, raw_type, "SUM", decimals, cuky_field, unit_field), None
        if field_role == "DIMENSION":
            return "DIMENSION", self._build_dimension_def(f, name, raw_type, is_key), None

        # PRIORITY 4: Reliable Business Metadata & Identifier Heuristics
        # Obvious dimension indicators despite numeric/DEC representation:
        dim_identifiers = {"ID", "NUM", "NUMBER", "NO", "CODE", "CD", "KEY", "PERIOD", "YEAR", "FISCPER", "POSTAL", "ZIP"}
        if is_key or any(tok in dim_identifiers for tok in tokens):
            return "DIMENSION", self._build_dimension_def(f, name, raw_type, is_key), None

        # Currency and Quantity data types:
        if raw_type == "CURR":
            return "MEASURE", self._build_measure_def(f, name, raw_type, "SUM", decimals, cuky_field, unit_field, unit_type="CURRENCY"), None
        if raw_type == "QUAN":
            return "MEASURE", self._build_measure_def(f, name, raw_type, "SUM", decimals, cuky_field, unit_field, unit_type="UNIT"), None

        # Obvious measure indicators:
        measure_identifiers = {"AMOUNT", "NETWR", "REVENUE", "QUANTITY", "QTY", "MENGE", "PRICE", "SALES", "COST", "TAX", "TOTAL", "BALANCE", "WEIGHT", "VOLUME"}
        if any(tok in measure_identifiers for tok in tokens):
            agg = "AVG" if "PRICE" in tokens or "TAX" in tokens else "SUM"
            return "MEASURE", self._build_measure_def(f, name, raw_type, agg, decimals, cuky_field, unit_field), None

        # PRIORITY 5: Ambiguity Handling
        # If numeric (DEC, INT, etc.) but no indicators matched, flag for review and default to Dimension
        numeric_types = {"DEC", "DECIMAL", "INT", "INTEGER", "INT4", "INT2", "FLTP", "FLOAT", "NUMC"}
        if raw_type in numeric_types:
            ambig = {
                "field_name": name,
                "data_type": raw_type,
                "review_reason": f"Field '{name}' of numeric type '{raw_type}' lacks explicit analytical semantics or aggregation metadata.",
                "assigned_default": "DIMENSION"
            }
            dim_def = self._build_dimension_def(f, name, raw_type, is_key)
            dim_def["review_required"] = True
            dim_def["review_reason"] = ambig["review_reason"]
            return "DIMENSION", dim_def, ambig

        # Default non-numeric: Dimension
        return "DIMENSION", self._build_dimension_def(f, name, raw_type, is_key), None

    def _build_measure_def(
        self,
        f: Dict[str, Any],
        name: str,
        raw_type: str,
        agg: str,
        decimals: int,
        cuky_field: Optional[str],
        unit_field: Optional[str],
        unit_type: Optional[str] = None
    ) -> Dict[str, Any]:
        m = {
            "id": name,
            "description": f.get("description") or name,
            "aggregation": agg,
            "scale": decimals,
            "dataType": "Decimal"
        }
        if unit_type == "CURRENCY" or raw_type == "CURR":
            m["unitType"] = "CURRENCY"
            ref = f.get("currency_unit_field") or cuky_field
            if ref:
                m["unitReferenceDimension"] = ref
        elif unit_type == "UNIT" or raw_type == "QUAN":
            m["unitType"] = "UNIT"
            ref = f.get("currency_unit_field") or unit_field
            if ref:
                m["unitReferenceDimension"] = ref
        return m

    def _build_dimension_def(self, f: Dict[str, Any], name: str, raw_type: str, is_key: bool) -> Dict[str, Any]:
        dim_type = "Date" if raw_type in ["DATS", "DATE"] else "Generic"
        return {
            "id": name,
            "description": f.get("description") or name,
            "type": dim_type,
            "isKey": is_key,
            "hasHierarchy": bool(f.get("has_hierarchy", False))
        }
