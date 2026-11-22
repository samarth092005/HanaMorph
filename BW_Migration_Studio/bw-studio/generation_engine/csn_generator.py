class DatasphereCSNGenerator:
    """
    Generates official SAP CSN v2.0 JSON definitions for SAP Datasphere.
    Supports Local Tables (entities), Views, and Analytic Models.
    """
    SAP_TYPE_MAP = {
        "CHAR": "cds.String",
        "NUMC": "cds.String",
        "DATS": "cds.Date",
        "TIMS": "cds.Time",
        "CURR": "cds.Decimal",
        "QUAN": "cds.Decimal",
        "DEC": "cds.Decimal",
        "INT4": "cds.Integer",
        "INT2": "cds.Integer",
        "CUKY": "cds.String",
        "UNIT": "cds.String"
    }

    def generate_entity_csn(self, space: str, target_name: str, fields: list, description: str = "") -> dict:
        elements = {}
        field_names = {f["field_name"] for f in fields}
        cuky_field = next((f["field_name"] for f in fields if f.get("data_type") == "CUKY" or f["field_name"] in ["CURRENCY", "WAERS"]), None)
        unit_field = next((f["field_name"] for f in fields if f.get("data_type") == "UNIT" or f["field_name"] in ["SALES_UNIT", "MEINS", "UNIT"]), None)

        for f in fields:
            f_name = f["field_name"]
            raw_type = f.get("data_type", "CHAR").upper()
            cds_type = self.SAP_TYPE_MAP.get(raw_type, "cds.String")
            
            elem_def = {"type": cds_type}
            if f.get("is_key"):
                elem_def["key"] = True
            if f.get("length") and cds_type == "cds.String":
                elem_def["length"] = int(f["length"])
            if cds_type == "cds.Decimal":
                elem_def["precision"] = int(f.get("length", 15))
                elem_def["scale"] = int(f.get("decimals", 2))
            if f.get("description"):
                elem_def["@EndUserText.label"] = f["description"]
            if f.get("semantics") == "AMO" or raw_type == "CURR":
                ref_cur = f.get("currency_unit_field") or cuky_field
                if ref_cur and ref_cur in field_names:
                    elem_def["@Semantics.amount.currencyCode"] = ref_cur
            if f.get("semantics") == "QUA" or raw_type == "QUAN":
                ref_unit = f.get("currency_unit_field") or unit_field
                if ref_unit and ref_unit in field_names:
                    elem_def["@Semantics.quantity.unitOfMeasure"] = ref_unit

            elements[f_name] = elem_def

        entity_id = f"{space}.{target_name}"
        return {
            "$schema": "https://help.sap.com/doc/csn-v2.0.json",
            "definitions": {
                entity_id: {
                    "kind": "entity",
                    "@EndUserText.label": description or target_name,
                    "elements": elements
                }
            }
        }

    def generate_view_csn(self, space: str, target_name: str, base_entity: str, fields: list, description: str = "") -> dict:
        elements = {}
        field_names = {f["field_name"] for f in fields}
        cuky_field = next((f["field_name"] for f in fields if f.get("data_type") == "CUKY" or f["field_name"] in ["CURRENCY", "WAERS"]), None)
        unit_field = next((f["field_name"] for f in fields if f.get("data_type") == "UNIT" or f["field_name"] in ["SALES_UNIT", "MEINS", "UNIT"]), None)

        for f in fields:
            f_name = f["field_name"]
            raw_type = f.get("data_type", "CHAR").upper()
            cds_type = self.SAP_TYPE_MAP.get(raw_type, "cds.String")
            elem_def = {"type": cds_type}
            if f.get("is_key"):
                elem_def["key"] = True
            if f.get("length") and cds_type == "cds.String":
                elem_def["length"] = int(f["length"])
            if cds_type == "cds.Decimal":
                elem_def["precision"] = int(f.get("length", 15))
                elem_def["scale"] = int(f.get("decimals", 2))
            if f.get("description"):
                elem_def["@EndUserText.label"] = f["description"]
            if f.get("semantics") == "AMO" or raw_type == "CURR":
                ref_cur = f.get("currency_unit_field") or cuky_field
                if ref_cur and ref_cur in field_names:
                    elem_def["@Semantics.amount.currencyCode"] = ref_cur
            if f.get("semantics") == "QUA" or raw_type == "QUAN":
                ref_unit = f.get("currency_unit_field") or unit_field
                if ref_unit and ref_unit in field_names:
                    elem_def["@Semantics.quantity.unitOfMeasure"] = ref_unit
            elements[f_name] = elem_def

        view_id = f"{space}.{target_name}"
        return {
            "$schema": "https://help.sap.com/doc/csn-v2.0.json",
            "definitions": {
                view_id: {
                    "kind": "view",
                    "@EndUserText.label": description or target_name,
                    "query": {
                        "from": f"{space}.{base_entity}",
                        "elements": elements
                    }
                }
            }
        }

    def generate_analytic_model_csn(self, space: str, target_name: str, base_entity: str, fields: list, description: str = "") -> dict:
        measures = []
        attributes = []
        for f in fields:
            if f.get("aggregation_type") == "SUM" or f.get("data_type") in ["CURR", "QUAN"]:
                measures.append(f["field_name"])
            else:
                attributes.append(f["field_name"])

        model_id = f"{space}.{target_name}"
        return {
            "$schema": "https://help.sap.com/doc/csn-v2.0.json",
            "definitions": {
                model_id: {
                    "kind": "view",
                    "@EndUserText.label": description or target_name,
                    "@Analytics.dataCategory": "CUBE",
                    "query": {
                        "from": f"{space}.{base_entity}",
                        "measures": measures,
                        "attributes": attributes
                    }
                }
            }
        }
