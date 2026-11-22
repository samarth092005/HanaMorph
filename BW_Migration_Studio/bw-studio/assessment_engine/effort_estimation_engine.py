"""
HANAMORPH — Explainable Migration Effort Estimation Engine
Milestone M3.5 / Workstream D

Estimates engineering effort in person-hours using transparent heuristic calibration:
- Base engineering effort from object type and complexity
- Dependency coupling and blast-radius multiplier
- Transformation redesign and ABAP refactoring overhead
- Semantic modeling and variable mapping effort
- Data reconciliation and 7-Level automated testing overhead

Outputs:
- low_hours, expected_hours, high_hours
- Explicit effort drivers
- Assumptions and heuristic calibration notices
"""

from typing import Dict, List, Optional, Any

class EffortEstimationEngine:
    BASE_HOURS_BY_TYPE = {
        "ADSO": 12.0,
        "ODSO": 14.0,
        "CUBE": 24.0,
        "COMPOSITE_PROVIDER": 16.0,
        "BW_QUERY": 14.0,
        "IOBJ": 6.0,
        "VIEW": 8.0,
        "RSDS": 8.0
    }

    def estimate_object_effort(
        self,
        object_name: str,
        complexity_data: Dict[str, Any],
        risk_data: Dict[str, Any],
        feasibility_data: Dict[str, Any],
        route_data: Dict[str, Any],
        obj_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates explainable effort estimates (low, expected, high person-hours).
        """
        obj_type = obj_record.get("type", "").upper()
        complexity_score = complexity_data.get("overall_complexity_score", 50)
        risk_score = risk_data.get("overall_risk_score", 50)
        has_custom_abap = "ABAP" in object_name.upper() or "ZSAM_FI" in object_name.upper()
        recommended_route = route_data.get("recommended_route", "native_datasphere")

        # 1. Base Architecture Effort
        base_hours = self.BASE_HOURS_BY_TYPE.get(obj_type, 10.0)
        complexity_multiplier = 0.6 + (complexity_score / 100.0) * 0.8  # Range: 0.6x to 1.4x
        core_modeling_hours = round(base_hours * complexity_multiplier, 1)

        drivers = [
            {
                "category": "Core Model Conversion",
                "hours": core_modeling_hours,
                "description": f"Base conversion and CSN schema mapping for {obj_type} (Complexity: {complexity_score}/100)."
            }
        ]

        # 2. Transformation & ABAP Refactoring Overhead
        transformation_hours = 0.0
        if has_custom_abap:
            if recommended_route == "bw_bridge":
                # Staged in BW Bridge -> less rewrite, mostly cloud ABAP compliance
                transformation_hours = 12.0
                drivers.append({
                    "category": "Clean Cloud ABAP Adaptation",
                    "hours": transformation_hours,
                    "description": "Refactor legacy ABAP statements for SAP BW Bridge Clean Cloud ABAP compatibility."
                })
            else:
                # Rewrite to native SQL / Python
                transformation_hours = 28.0
                drivers.append({
                    "category": "ABAP-to-SQL Logic Rewrite",
                    "hours": transformation_hours,
                    "description": "Manually re-engineer procedural ABAP routines into SQLScript views or Transformation Flows."
                })
        elif complexity_data.get("dimensions", {}).get("transformation", {}).get("score", 0) > 40:
            transformation_hours = 6.0
            drivers.append({
                "category": "Currency/Unit Translation Mapping",
                "hours": transformation_hours,
                "description": "Configure Datasphere currency translation rules and reference table links."
            })

        # 3. Dependency & Coupling Overhead
        dependency_hours = 0.0
        downstream_count = complexity_data.get("evidence", {}).get("fan_out", 0)
        if downstream_count >= 5:
            dependency_hours = 10.0
            drivers.append({
                "category": "High-Coupling Integration & Lineage",
                "hours": dependency_hours,
                "description": f"Verify and sequence {downstream_count} downstream consumer bindings."
            })
        elif downstream_count >= 2:
            dependency_hours = 4.0
            drivers.append({
                "category": "Consumer Integration",
                "hours": dependency_hours,
                "description": f"Verify {downstream_count} downstream consumer bindings."
            })

        # 4. Testing & Validation Overhead (Automated 7-Level Validation + Reconciliation)
        if risk_score >= 60:
            testing_hours = 12.0
            drivers.append({
                "category": "Deep Data Profiling & Parity Testing",
                "hours": testing_hours,
                "description": "Execute automated Level 1-7 checks with sample record reconciliation."
            })
        else:
            testing_hours = 6.0
            drivers.append({
                "category": "Standard Automated Validation",
                "hours": testing_hours,
                "description": "Execute automated CSN syntax, schema matching, and integrity checks."
            })

        # Calculate Total Expected Effort
        expected_total = round(core_modeling_hours + transformation_hours + dependency_hours + testing_hours, 1)

        # Range calculation: -20% Low, +35% High based on risk
        risk_uncertainty_factor = 0.20 + (risk_score / 100.0) * 0.25  # Range: 20% to 45%
        low_hours = max(2.0, round(expected_total * (1.0 - 0.20), 1))
        high_hours = round(expected_total * (1.0 + risk_uncertainty_factor), 1)

        # Assumptions
        assumptions = [
            "Estimates assume developer proficiency in SAP Datasphere and SAP BW 7.5.",
            "Automated tools (HANAMORPH CSN & SQL generators) generate initial artifacts in seconds.",
            "Testing hours reflect end-to-end data reconciliation, user acceptance testing, and validation.",
            "Estimates are heuristic benchmarks and should be calibrated with team velocity."
        ]

        confidence = 0.85 if complexity_data.get("confidence_score", 0.8) > 0.8 else 0.70

        return {
            "object_name": object_name,
            "expected_hours": expected_total,
            "low_hours": low_hours,
            "high_hours": high_hours,
            "confidence": confidence,
            "effort_tier": "HIGH" if expected_total >= 35 else ("MEDIUM" if expected_total >= 18 else "LOW"),
            "effort_drivers": drivers,
            "assumptions": assumptions,
            "heuristic_notice": "HEURISTIC ESTIMATE: Calibrated on typical SAP migration project work breakdown structures."
        }
