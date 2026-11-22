"""
HANAMORPH — SAP BW Modernization Feasibility Engine
Milestone M3.3: Objective Readiness & Feasibility Classification

Classifies objects into 6 distinct architectural feasibility states:
- READY_FOR_MODERNIZATION: Clean relational schema, zero custom code, direct target mapping.
- READY_WITH_REMEDIATION: Standard model with minor remediations (e.g., currency table associations, surrogate keys).
- REQUIRES_REDESIGN: Complex multidimensional/composite model requiring architectural decomposition.
- HIGH_RISK: Procedural ABAP transformation routines, high blast-radius dependency coupling.
- BLOCKED: Missing prerequisites, unsupported constructs on target platform, or unresolvable circular ETL.
- INSUFFICIENT_EVIDENCE: Object metadata incomplete or unverified.
"""

from typing import Dict, List, Optional, Any

class FeasibilityEngine:
    def __init__(self, complexity_engine=None, risk_engine=None):
        self.complexity_engine = complexity_engine
        self.risk_engine = risk_engine

    def evaluate_feasibility(self, object_name: str, complexity_data: Dict[str, Any], risk_data: Dict[str, Any], obj_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes the definitive modernization feasibility state with explainable rationale.
        """
        complexity_score = complexity_data.get("overall_complexity_score", 50)
        risk_score = risk_data.get("overall_risk_score", 50)
        risk_level = risk_data.get("risk_level", "MEDIUM")
        provenance = obj_record.get("provenance", "UNKNOWN")
        obj_type = obj_record.get("type", "").upper()
        has_custom_abap = "ABAP" in object_name.upper() or "ZSAM_FI" in object_name.upper()
        field_count = complexity_data.get("evidence", {}).get("field_count", 0)

        # 1. Check for Insufficient Evidence
        if provenance == "UNKNOWN" or (field_count == 0 and obj_type not in ["COMPOSITE_PROVIDER", "BW_QUERY", "VIEW"]):
            status = "INSUFFICIENT_EVIDENCE"
            rationale = "Metadata attributes are incomplete or unverified. Live DDIC inspection or Eclipse cache required."
            action = "Trigger ADT DDIC extraction or import metadata bundle."
        
        # 2. Check for Blocked Status
        elif obj_type == "ODSV":
            status = "BLOCKED"
            rationale = "Open ODS Views are unsupported on source SAP S21 NetWeaver 7.53 and require HANA Cloud Virtual Table."
            action = "Replace with Datasphere Remote Table directly connected to source database."
        
        # 3. Check for High Risk / Critical Redesign
        elif has_custom_abap and risk_score >= 70:
            status = "HIGH_RISK"
            rationale = "Procedural ABAP routines present high regression risk. Requires SAP BW Bridge runtime or manual SQLScript refactoring."
            action = "Route to SAP BW Bridge or assign senior ABAP/HANA developer for SQL rewrite."
        
        # 4. Check for Architectural Redesign
        elif obj_type == "CUBE" or complexity_score >= 75:
            status = "REQUIRES_REDESIGN"
            rationale = "Legacy multidimensional/cube structure must be redesigned into Star Join Analytic Model."
            action = "Decompose dimension tables into Datasphere Dimension Views and recreate Star Join."
        
        # 5. Check for Ready with Remediation
        elif complexity_score >= 45 or risk_score >= 40 or any(f.get("factor") == "Data Precision & Currencies" for f in risk_data.get("contributing_factors", [])):
            status = "READY_WITH_REMEDIATION"
            rationale = "Feasible for cloud migration with minor configuration (e.g. currency conversion tables TCURR, surrogate key assignments)."
            action = "Automated CSN generation with currency reference mapping."
        
        # 6. Ready for Modernization
        else:
            status = "READY_FOR_MODERNIZATION"
            rationale = "Standard relational persistence with primary keys and verified schema. 100% automated conversion supported."
            action = "Proceed with automated Native Datasphere CSN and SQL DDL generation."

        return {
            "object_name": object_name,
            "feasibility_status": status,
            "feasibility_rationale": rationale,
            "recommended_action": action,
            "complexity_score": complexity_score,
            "risk_score": risk_score,
            "risk_level": risk_level
        }
