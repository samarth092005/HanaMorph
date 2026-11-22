"""
HANAMORPH — Multi-Target Compatibility & Architecture Route Evaluator
Milestone M3.4 / Workstream C

Evaluates 4 independent target modernization routes across 5 weighted dimensions:
- Functional Compatibility: 35%
- Technical Compatibility: 25%
- Process Compatibility: 15%
- Roles and Activation: 15%
- Platform Compatibility: 10%

Target Routes:
1. Native SAP Datasphere (Local Table, Graphical View, SQL View, Analytic Model)
2. SAP BW Bridge (ABAP runtime preservation, cloud-hosted BW/4HANA ADSOs)
3. Business Data Cloud / BDC (Data Product contracts, Open Data Fabric)
4. Hybrid Modernization (Staged BW Bridge extraction + Datasphere Analytic Model)
"""

from typing import Dict, List, Optional, Any

class TargetCompatibilityEngine:
    DIMENSION_WEIGHTS = {
        "functional": 0.35,
        "technical": 0.25,
        "process": 0.15,
        "roles": 0.15,
        "platform": 0.10
    }

    def evaluate_all_routes(self, object_name: str, complexity_data: Dict[str, Any], risk_data: Dict[str, Any], obj_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates independent compatibility scores and feasibility for all 4 target routes.
        """
        has_custom_abap = "ABAP" in object_name.upper() or "ZSAM_FI" in object_name.upper()
        obj_type = obj_record.get("type", "").upper()
        field_count = complexity_data.get("evidence", {}).get("field_count", 0)
        key_count = complexity_data.get("evidence", {}).get("key_count", 0)
        has_curr_quan = any(d.get("factor") == "Data Precision & Currencies" for d in risk_data.get("contributing_factors", []))

        routes = {}

        # -------------------------------------------------------------
        # Route 1: Native SAP Datasphere
        # -------------------------------------------------------------
        if has_custom_abap:
            ds_func = 40
            ds_tech = 35
            ds_proc = 60
            ds_role = 80
            ds_plat = 40
            ds_feasibility = "REQUIRES_REFACTORING"
            ds_changes = [
                "Refactor procedural ABAP transformation routines into SQLScript views or Transformation Flows",
                "Replace custom exit formulas with Datasphere calculated columns"
            ]
            ds_risks = ["Semantic drift during ABAP-to-SQL logic rewrite", "Calculation precision differences"]
            ds_unsupported = ["ABAP start/expert routines", "SAP GUI dynpro screens"]
        elif obj_type == "COMPOSITE_PROVIDER":
            ds_func = 95
            ds_tech = 92
            ds_proc = 90
            ds_role = 95
            ds_plat = 95
            ds_feasibility = "HIGHLY_COMPATIBLE"
            ds_changes = ["Convert part-provider Join/Union mappings to Datasphere Graphical View or Analytic Model"]
            ds_risks = ["Complex Multi-join query performance requires partition indexing"]
            ds_unsupported = []
        elif obj_type == "ADSO":
            ds_func = 92
            ds_tech = 95 if key_count > 0 else 80
            ds_proc = 90
            ds_role = 90 if has_curr_quan else 95
            ds_plat = 95
            ds_feasibility = "HIGHLY_COMPATIBLE"
            ds_changes = [
                "Deploy Datasphere Local Table via CSN 2.0 schema",
                "Configure replication via Replication Flow or DP Agent"
            ]
            if has_curr_quan:
                ds_changes.append("Associate currency reference tables TCURR/T006 in space")
            ds_risks = ["Delta merge load on HANA Cloud storage"]
            ds_unsupported = []
        elif obj_type == "BW_QUERY":
            ds_func = 85
            ds_tech = 88
            ds_proc = 85
            ds_role = 90
            ds_plat = 90
            ds_feasibility = "COMPATIBLE"
            ds_changes = ["Map BEx query measures, dimensions, and variables into Datasphere Analytic Model"]
            ds_risks = ["BEx exit variables require replacement with SAC input parameters"]
            ds_unsupported = ["Complex BEx customer-exit variables (requires SAC script)"]
        else:
            ds_func = 80
            ds_tech = 80
            ds_proc = 80
            ds_role = 85
            ds_plat = 85
            ds_feasibility = "COMPATIBLE"
            ds_changes = ["Generate CSN 2.0 and HANA SQL DDL"]
            ds_risks = []
            ds_unsupported = []

        ds_score = int(round(
            ds_func * self.DIMENSION_WEIGHTS["functional"] +
            ds_tech * self.DIMENSION_WEIGHTS["technical"] +
            ds_proc * self.DIMENSION_WEIGHTS["process"] +
            ds_role * self.DIMENSION_WEIGHTS["roles"] +
            ds_plat * self.DIMENSION_WEIGHTS["platform"]
        ))
        routes["native_datasphere"] = {
            "route_id": "native_datasphere",
            "display_name": "Native Datasphere",
            "compatibility_score": ds_score,
            "feasibility": ds_feasibility,
            "target_construct": "Local Table / Analytic Model" if obj_type != "BW_QUERY" else "Analytic Model",
            "required_changes": ds_changes,
            "technical_risks": ds_risks,
            "unsupported_capabilities": ds_unsupported,
            "dimension_scores": {
                "functional": ds_func, "technical": ds_tech, "process": ds_proc, "roles": ds_role, "platform": ds_plat
            },
            "confidence": 0.95
        }

        # -------------------------------------------------------------
        # Route 2: SAP BW Bridge
        # -------------------------------------------------------------
        if has_custom_abap:
            br_func = 95
            br_tech = 92
            br_proc = 85
            br_role = 85
            br_plat = 90
            br_feasibility = "RECOMMENDED_TARGET"
            br_changes = [
                "Preserve procedural ABAP logic within SAP BW Bridge runtime",
                "Verify ABAP language version compliance (ABAP for Cloud Development / Clean ABAP rules)"
            ]
            br_risks = ["Classic non-cloud ABAP statements require modernization to Clean Cloud ABAP"]
            br_unsupported = ["Direct direct-to-database bypass (Native SQL)", "Obsolete function modules"]
        elif obj_type in ["ADSO", "COMPOSITE_PROVIDER"]:
            br_func = 90
            br_tech = 88
            br_proc = 80
            br_role = 85
            br_plat = 85
            br_feasibility = "COMPATIBLE"
            br_changes = ["Stage in BW Bridge ADSO and expose via Remote Table to Datasphere space"]
            br_risks = ["Dual maintenance footprint across BW Bridge and Datasphere"]
            br_unsupported = []
        else:
            br_func = 70
            br_tech = 70
            br_proc = 70
            br_role = 75
            br_plat = 75
            br_feasibility = "SUB_OPTIMAL"
            br_changes = ["Object does not benefit from BW Bridge runtime"]
            br_risks = ["Unnecessary infrastructure cost for standard tabular schema"]
            br_unsupported = ["Direct front-end analytical consumption (requires Datasphere exposure)"]

        br_score = int(round(
            br_func * self.DIMENSION_WEIGHTS["functional"] +
            br_tech * self.DIMENSION_WEIGHTS["technical"] +
            br_proc * self.DIMENSION_WEIGHTS["process"] +
            br_role * self.DIMENSION_WEIGHTS["roles"] +
            br_plat * self.DIMENSION_WEIGHTS["platform"]
        ))
        routes["bw_bridge"] = {
            "route_id": "bw_bridge",
            "display_name": "SAP BW Bridge",
            "compatibility_score": br_score,
            "feasibility": br_feasibility,
            "target_construct": "Cloud ADSO / BW Bridge Flow",
            "required_changes": br_changes,
            "technical_risks": br_risks,
            "unsupported_capabilities": br_unsupported,
            "dimension_scores": {
                "functional": br_func, "technical": br_tech, "process": br_proc, "roles": br_role, "platform": br_plat
            },
            "confidence": 0.90
        }

        # -------------------------------------------------------------
        # Route 3: Business Data Cloud (BDC)
        # -------------------------------------------------------------
        if obj_type in ["COMPOSITE_PROVIDER", "BW_QUERY"]:
            bdc_func = 85
            bdc_tech = 80
            bdc_proc = 85
            bdc_role = 90
            bdc_plat = 85
            bdc_feasibility = "COMPATIBLE"
            bdc_changes = [
                "Package semantic model into published BDC Data Product",
                "Define business metadata, ownership, SLA, and semantic data contract"
            ]
            bdc_risks = ["Data contract governance alignment across consuming domains"]
            bdc_unsupported = []
        elif obj_type == "ADSO" and key_count > 0:
            bdc_func = 80
            bdc_tech = 80
            bdc_proc = 80
            bdc_role = 85
            bdc_plat = 85
            bdc_feasibility = "COMPATIBLE"
            bdc_changes = ["Publish standardized master/transactional dataset as Data Product entity"]
            bdc_risks = ["Requires curation and schema stabilization before publication"]
            bdc_unsupported = []
        else:
            bdc_func = 65
            bdc_tech = 65
            bdc_proc = 70
            bdc_role = 75
            bdc_plat = 70
            bdc_feasibility = "SUB_OPTIMAL"
            bdc_changes = ["Underlying technical staging structure not suitable as standalone business data product"]
            bdc_risks = ["Exposing uncurated staging tables violates data fabric governance"]
            bdc_unsupported = ["Staging changelogs / inbound queues"]

        bdc_score = int(round(
            bdc_func * self.DIMENSION_WEIGHTS["functional"] +
            bdc_tech * self.DIMENSION_WEIGHTS["technical"] +
            bdc_proc * self.DIMENSION_WEIGHTS["process"] +
            bdc_role * self.DIMENSION_WEIGHTS["roles"] +
            bdc_plat * self.DIMENSION_WEIGHTS["platform"]
        ))
        routes["bdc"] = {
            "route_id": "bdc",
            "display_name": "Business Data Cloud (BDC)",
            "compatibility_score": bdc_score,
            "feasibility": bdc_feasibility,
            "target_construct": "Governed Data Product",
            "required_changes": bdc_changes,
            "technical_risks": bdc_risks,
            "unsupported_capabilities": bdc_unsupported,
            "dimension_scores": {
                "functional": bdc_func, "technical": bdc_tech, "process": bdc_proc, "roles": bdc_role, "platform": bdc_plat
            },
            "confidence": 0.85
        }

        # -------------------------------------------------------------
        # Route 4: Hybrid Modernization
        # -------------------------------------------------------------
        if has_custom_abap:
            hyb_func = 92
            hyb_tech = 90
            hyb_proc = 88
            hyb_role = 90
            hyb_plat = 92
            hyb_feasibility = "RECOMMENDED_TARGET"
            hyb_changes = [
                "Stage complex extraction and ABAP transformations in SAP BW Bridge",
                "Federate or replicate prepared datasets into Native Datasphere Space",
                "Build modern SAC consumption stories over Datasphere Analytic Models"
            ]
            hyb_risks = ["Latency across Bridge-to-Datasphere space replication"]
            hyb_unsupported = []
        else:
            hyb_func = 85
            hyb_tech = 85
            hyb_proc = 85
            hyb_role = 88
            hyb_plat = 88
            hyb_feasibility = "COMPATIBLE"
            hyb_changes = ["Standard multi-tier cloud modernization architecture"]
            hyb_risks = ["Additional architectural components to monitor"]
            hyb_unsupported = []

        hyb_score = int(round(
            hyb_func * self.DIMENSION_WEIGHTS["functional"] +
            hyb_tech * self.DIMENSION_WEIGHTS["technical"] +
            hyb_proc * self.DIMENSION_WEIGHTS["process"] +
            hyb_role * self.DIMENSION_WEIGHTS["roles"] +
            hyb_plat * self.DIMENSION_WEIGHTS["platform"]
        ))
        routes["hybrid"] = {
            "route_id": "hybrid",
            "display_name": "Hybrid Modernization",
            "compatibility_score": hyb_score,
            "feasibility": hyb_feasibility,
            "target_construct": "Staged Bridge + Datasphere Semantic Model",
            "required_changes": hyb_changes,
            "technical_risks": hyb_risks,
            "unsupported_capabilities": hyb_unsupported,
            "dimension_scores": {
                "functional": hyb_func, "technical": hyb_tech, "process": hyb_proc, "roles": hyb_role, "platform": hyb_plat
            },
            "confidence": 0.90
        }

        # Determine Primary Recommendation
        recommended_route = max(routes.values(), key=lambda r: r["compatibility_score"])

        return {
            "object_name": object_name,
            "recommended_route": recommended_route["route_id"],
            "recommended_target": recommended_route["display_name"],
            "recommended_target_construct": recommended_route["target_construct"],
            "recommendation_rationale": f"Highest multi-dimensional compatibility ({recommended_route['compatibility_score']}/100) with feasibility '{recommended_route['feasibility']}'.",
            "routes": routes
        }
