"""
HANAMORPH — Modernization Prioritization & Migration Wave Sequencer
Milestone M3.6 / Workstream E

Prioritizes and sequences modernization candidates using multi-factor ranking:
- Modernization Readiness & Feasibility State
- Technical Complexity & Migration Risk
- Downstream Consumer Fan-out (Value Multiplier)
- Estimated Engineering Effort
- Topological Dependency Order (Zero-Broken-Lineage Constraint)

Output Categories:
- QUICK_WINS (Early value, minimal risk)
- HIGH_VALUE_CANDIDATES (Core semantic models feeding reporting)
- STANDARD_MIGRATION (Standard relational persistence)
- HIGH_RISK_CANDIDATES (Requires senior engineering attention)
- REDESIGN_REQUIRED (Architectural restructuring required)
- BLOCKED (Unresolved prerequisites)
"""

from typing import Dict, List, Optional, Any

class PrioritizationEngine:
    def __init__(self, dependency_graph=None):
        self.dependency_graph = dependency_graph

    def prioritize_objects(self, assessed_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Classifies and ranks assessed objects, outputting categorized cohorts and an ordered migration sequence.
        """
        quick_wins = []
        high_value = []
        standard = []
        high_risk = []
        redesign_required = []
        blocked = []

        for item in assessed_objects:
            obj_name = item["object_name"]
            feasibility = item.get("feasibility_status", "READY_FOR_MODERNIZATION")
            complexity_score = item.get("complexity_score", 50)
            risk_score = item.get("risk_score", 50)
            expected_hours = item.get("effort", {}).get("expected_hours", 20.0)
            comp_obj = item.get("complexity_details") if isinstance(item.get("complexity_details"), dict) else (item.get("complexity") if isinstance(item.get("complexity"), dict) else {})
            downstream_count = comp_obj.get("evidence", {}).get("fan_out", 0)

            # Classification Logic
            if feasibility == "BLOCKED" or feasibility == "INSUFFICIENT_EVIDENCE":
                blocked.append(item)
                item["priority_tier"] = "BLOCKED"
            elif feasibility == "REQUIRES_REDESIGN":
                redesign_required.append(item)
                item["priority_tier"] = "REDESIGN_REQUIRED"
            elif feasibility == "HIGH_RISK" or risk_score >= 65:
                high_risk.append(item)
                item["priority_tier"] = "HIGH_RISK"
            elif downstream_count >= 2 or item.get("object_type") in ["COMPOSITE_PROVIDER", "BW_QUERY"]:
                high_value.append(item)
                item["priority_tier"] = "HIGH_VALUE"
            elif complexity_score < 45 and risk_score < 35 and expected_hours < 18.0:
                quick_wins.append(item)
                item["priority_tier"] = "QUICK_WIN"
            else:
                standard.append(item)
                item["priority_tier"] = "STANDARD"

        # Sort within cohorts
        quick_wins.sort(key=lambda x: (x.get("risk_score", 0), x.get("complexity_score", 0)))
        def _get_fan_out(x):
            c = x.get("complexity_details") if isinstance(x.get("complexity_details"), dict) else (x.get("complexity") if isinstance(x.get("complexity"), dict) else {})
            return c.get("evidence", {}).get("fan_out", 0)
        high_value.sort(key=_get_fan_out, reverse=True)
        high_risk.sort(key=lambda x: x.get("risk_score", 0), reverse=True)

        # Topological Sequence Alignment
        topological_order = []
        if self.dependency_graph:
            try:
                topo = self.dependency_graph.get_topological_order()
                topological_order = topo.get("sequence", [])
            except Exception:
                topological_order = []

        all_names = [item["object_name"] for item in assessed_objects]
        name_to_item = {item["object_name"]: item for item in assessed_objects}

        # If topological order exists, sequence items according to dependency order
        ordered_sequence = []
        if topological_order:
            for name in topological_order:
                if name in name_to_item:
                    ordered_sequence.append(name_to_item[name])
            # Append any items not in topological sort
            for item in assessed_objects:
                if item["object_name"] not in topological_order:
                    ordered_sequence.append(item)
        else:
            # Fallback: Quick Wins -> Standard -> High Value -> Redesign -> High Risk -> Blocked
            ordered_sequence = quick_wins + standard + high_value + redesign_required + high_risk + blocked

        # Assign Waves (Wave 1: Quick Wins / Staging, Wave 2: Standard Entities, Wave 3: Semantics, Wave 4: Complex Redesign)
        total_items = len(ordered_sequence)
        wave_size = max(1, (total_items + 2) // 3)
        waves_dict = {}
        for idx, item in enumerate(ordered_sequence):
            w_num = (idx // wave_size) + 1
            item["recommended_wave"] = w_num
            w_key = f"wave_{w_num}"
            if w_key not in waves_dict:
                waves_dict[w_key] = []
            waves_dict[w_key].append(item)

        return {
            "total_objects_prioritized": len(assessed_objects),
            "summary_counts": {
                "quick_wins": len(quick_wins),
                "high_value": len(high_value),
                "standard": len(standard),
                "high_risk": len(high_risk),
                "redesign_required": len(redesign_required),
                "blocked": len(blocked)
            },
            "cohorts": {
                "quick_wins": [x["object_name"] for x in quick_wins],
                "high_value_candidates": [x["object_name"] for x in high_value],
                "standard_migration": [x["object_name"] for x in standard],
                "high_risk_candidates": [x["object_name"] for x in high_risk],
                "redesign_required": [x["object_name"] for x in redesign_required],
                "blocked": [x["object_name"] for x in blocked]
            },
            "waves": waves_dict,
            "recommended_migration_sequence": [
                {
                    "rank": idx + 1,
                    "object_name": item["object_name"],
                    "object_type": item.get("object_type", "ADSO"),
                    "priority_tier": item.get("priority_tier", "STANDARD"),
                    "recommended_route": item.get("recommended_route", "native_datasphere"),
                    "recommended_wave": item.get("recommended_wave", 1),
                    "expected_hours": item.get("effort", {}).get("expected_hours", 12.0)
                }
                for idx, item in enumerate(ordered_sequence)
            ]
        }
