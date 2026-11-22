"""
HANAMORPH — Master Modernization Assessment & Intelligence Engine
Milestone M3: Integrated Discovery Closure & Modernization Intelligence

Orchestrates multi-dimensional evaluation:
- Complexity Engine (7 dimensions)
- Migration Risk Engine (7 factors)
- Feasibility Engine (6 architectural states)
- Target Compatibility Engine (4 independent routes)
- Effort Estimation Engine (heuristic person-hours)
- Prioritization Engine (cohort ranking & wave sequence)
- Landscape Intelligence (live repository metrics)
"""

import sqlite3
import uuid
import json
import time
from typing import Dict, List, Optional, Any
from database.sqlite_queue import SingleWriterQueue
from .complexity_engine import ComplexityEngine
from .migration_risk_engine import MigrationRiskEngine
from .feasibility_engine import FeasibilityEngine
from .target_compatibility_engine import TargetCompatibilityEngine
from .effort_estimation_engine import EffortEstimationEngine
from .prioritization_engine import PrioritizationEngine
from .landscape_intelligence import LandscapeIntelligence

class AssessmentEngine:
    WEIGHTS = {
        "functional": 0.35,
        "technical": 0.25,
        "process": 0.15,
        "roles": 0.15,
        "platform": 0.10
    }

    def __init__(self, db_path: str, dependency_graph=None):
        self.db_path = db_path
        self.dependency_graph = dependency_graph
        self.complexity_engine = ComplexityEngine(db_path, dependency_graph)
        self.risk_engine = MigrationRiskEngine(db_path, dependency_graph)
        self.feasibility_engine = FeasibilityEngine(self.complexity_engine, self.risk_engine)
        self.target_engine = TargetCompatibilityEngine()
        self.effort_engine = EffortEstimationEngine()
        self.prioritization_engine = PrioritizationEngine(dependency_graph)
        self.landscape_engine = LandscapeIntelligence(
            db_path, self.complexity_engine, self.risk_engine, self.target_engine, self.effort_engine
        )

    def assess_object(self, object_name: str) -> dict:
        """
        Deep multi-factor modernization evaluation for a single SAP BW object.
        Consumes real repository metadata and dependency topology.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM bw_objects WHERE technical_name = ?", (object_name,))
        obj = cur.fetchone()
        if not obj:
            conn.close()
            raise ValueError(f"Object '{object_name}' not found in discovery catalog.")

        obj_dict = dict(obj)
        obj_type = obj_dict.get("type", "ADSO")

        cur.execute("SELECT * FROM bw_object_fields WHERE object_name = ?", (object_name,))
        fields = [dict(f) for f in cur.fetchall()]

        cur.execute("""
            SELECT * FROM bw_object_dependencies 
            WHERE source_object = ? OR dependent_object = ?
        """, (object_name, object_name))
        deps = [dict(d) for d in cur.fetchall()]
        conn.close()

        # Run specialized sub-engines
        comp_eval = self.complexity_engine.evaluate_object_complexity(object_name)
        risk_eval = self.risk_engine.evaluate_object_risk(object_name)
        feas_eval = self.feasibility_engine.evaluate_feasibility(object_name, comp_eval, risk_eval, obj_dict)
        route_eval = self.target_engine.evaluate_all_routes(object_name, comp_eval, risk_eval, obj_dict)
        effort_eval = self.effort_engine.estimate_object_effort(object_name, comp_eval, risk_eval, feas_eval, route_eval, obj_dict)

        # Map to standard 5 dimensions for backward compatibility
        rec_target = route_eval["recommended_target"]
        rec_route_id = route_eval["recommended_route"]
        rec_route_data = route_eval["routes"].get(rec_route_id, {})
        dim_scores = rec_route_data.get("dimension_scores", {
            "functional": 90, "technical": 85, "process": 85, "roles": 90, "platform": 90
        })

        overall_score = rec_route_data.get("compatibility_score", 88)
        complexity_category = comp_eval.get("complexity_category", "LOW")
        risk_level = risk_eval.get("risk_level", "LOW")

        findings = {
            "functional": {
                "score": dim_scores["functional"],
                "weight": self.WEIGHTS["functional"],
                "finding": f"Functional suitability for {rec_target}."
            },
            "technical": {
                "score": dim_scores["technical"],
                "weight": self.WEIGHTS["technical"],
                "finding": f"Technical schema and DDL conversion for {rec_target}."
            },
            "process": {
                "score": dim_scores["process"],
                "weight": self.WEIGHTS["process"],
                "finding": "Data ingestion and staging process compatibility."
            },
            "roles": {
                "score": dim_scores["roles"],
                "weight": self.WEIGHTS["roles"],
                "finding": "Security and authorization reference mapping."
            },
            "platform": {
                "score": dim_scores["platform"],
                "weight": self.WEIGHTS["platform"],
                "finding": "Target cloud environment platform compatibility."
            }
        }

        confidence_score = comp_eval.get("confidence_score", 0.90)
        confidence_level = "VERY_HIGH" if confidence_score >= 0.9 else ("HIGH" if confidence_score >= 0.8 else "MEDIUM")

        return {
            "object_name": object_name,
            "type": obj_type,
            "recommended_target": rec_target,
            "recommended_route": rec_route_id,
            "modernization_approach": route_eval.get("recommendation_rationale", ""),
            "overall_score": overall_score,
            "confidence_score": confidence_score,
            "confidence_level": confidence_level,
            "confidence_rationale": f"Calculated from {obj_dict.get('provenance', 'LIVE_VERIFIED')} metadata with {len(fields)} fields.",
            "scores": dim_scores,
            "complexity": complexity_category,
            "risk_level": risk_level,
            "risk_rationale": risk_eval.get("contributing_factors", [{}])[0].get("detail", "Standard migration profile."),
            "blast_radius_score": len(deps) + 1,
            "feasibility_status": feas_eval.get("feasibility_status", "READY_FOR_MODERNIZATION"),
            "feasibility_details": feas_eval,
            "complexity_details": comp_eval,
            "risk_details": risk_eval,
            "route_evaluations": route_eval["routes"],
            "effort_estimate": effort_eval,
            "findings": findings,
            "rationale": route_eval.get("recommendation_rationale", "Standard modernization path.")
        }

    def assess_all(self, system_id: str = "S21") -> dict:
        """
        Runs comprehensive M3 intelligence across all objects for system_id.
        Persists results idempotently into SQLite via SingleWriterQueue.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Handle system_id variations (S21, S21_LIVE)
        cur.execute("SELECT technical_name FROM bw_objects WHERE system_id LIKE ? ORDER BY technical_name ASC", (f"%{system_id[:3]}%",))
        object_names = [r[0] for r in cur.fetchall()]
        if not object_names:
            cur.execute("SELECT technical_name FROM bw_objects ORDER BY technical_name ASC")
            object_names = [r[0] for r in cur.fetchall()]
        conn.close()

        run_id = f"assess-{uuid.uuid4().hex[:8]}"
        stmts = [("""
            INSERT INTO assessment_runs (id, system_id, model_version, total_objects, run_timestamp)
            VALUES (?, ?, '3.0.0', ?, CURRENT_TIMESTAMP)
        """, (run_id, system_id, len(object_names)))]

        results = []
        for name in object_names:
            assessment = self.assess_object(name)
            results.append(assessment)

            # 1. Legacy findings table
            stmts.append(("""
                INSERT INTO assessment_findings (
                    assessment_run_id, object_name, recommended_target, overall_score,
                    functional_score, technical_score, process_score, role_score, platform_score,
                    complexity, risk_level, findings_json, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(assessment_run_id, object_name) DO UPDATE SET
                    overall_score = excluded.overall_score,
                    recommended_target = excluded.recommended_target,
                    rationale = excluded.rationale
            """, (
                run_id, name, assessment["recommended_target"], assessment["overall_score"],
                assessment["scores"]["functional"], assessment["scores"]["technical"],
                assessment["scores"]["process"], assessment["scores"]["roles"],
                assessment["scores"]["platform"], assessment["complexity"],
                assessment["risk_level"], json.dumps(assessment["findings"]), assessment["rationale"]
            )))

            # 2. Modernization assessments table (Migration 7)
            eff = assessment["effort_estimate"]
            stmts.append(("""
                INSERT INTO modernization_assessments (
                    id, assessment_run_id, object_name, urn, feasibility_status,
                    complexity_score, complexity_category, risk_score, risk_level,
                    recommended_route, recommended_approach, effort_low_hours,
                    effort_expected_hours, effort_high_hours, priority_tier,
                    confidence_score, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(assessment_run_id, object_name) DO UPDATE SET
                    feasibility_status = excluded.feasibility_status,
                    complexity_score = excluded.complexity_score,
                    risk_score = excluded.risk_score,
                    recommended_route = excluded.recommended_route,
                    effort_expected_hours = excluded.effort_expected_hours,
                    details_json = excluded.details_json
            """, (
                f"mod-{uuid.uuid4().hex[:8]}", run_id, name, f"urn:sap:bw:s21:200:{assessment['type'].lower()}:{name.lower()}",
                assessment["feasibility_status"], assessment["complexity_details"]["overall_complexity_score"],
                assessment["complexity"], assessment["risk_details"]["overall_risk_score"], assessment["risk_level"],
                assessment["recommended_route"], assessment["modernization_approach"],
                eff["low_hours"], eff["expected_hours"], eff["high_hours"],
                "STANDARD", assessment["confidence_score"], json.dumps({
                    "complexity": assessment["complexity_details"],
                    "risk": assessment["risk_details"],
                    "routes": assessment["route_evaluations"],
                    "effort": assessment["effort_estimate"]
                })
            )))

            # 3. Route evaluations table (Migration 7)
            for r_id, r_info in assessment["route_evaluations"].items():
                stmts.append(("""
                    INSERT INTO route_evaluations (
                        assessment_run_id, object_name, route_id, compatibility_score,
                        feasibility, required_changes_json, technical_risks_json,
                        unsupported_capabilities_json, estimated_effort_hours, confidence,
                        evidence_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(assessment_run_id, object_name, route_id) DO UPDATE SET
                        compatibility_score = excluded.compatibility_score,
                        feasibility = excluded.feasibility
                """, (
                    run_id, name, r_id, r_info["compatibility_score"], r_info["feasibility"],
                    json.dumps(r_info.get("required_changes", [])),
                    json.dumps(r_info.get("technical_risks", [])),
                    json.dumps(r_info.get("unsupported_capabilities", [])),
                    eff["expected_hours"], r_info.get("confidence", 0.9),
                    json.dumps(r_info.get("dimension_scores", {}))
                )))

            # 4. Complexity breakdowns table (Migration 7)
            comp_d = assessment["complexity_details"]["dimensions"]
            stmts.append(("""
                INSERT INTO complexity_breakdowns (
                    object_name, structural_score, dependency_score, transformation_score,
                    data_model_score, semantic_score, customization_score, operational_score,
                    overall_score, complexity_category, drivers_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(object_name) DO UPDATE SET
                    overall_score = excluded.overall_score,
                    complexity_category = excluded.complexity_category,
                    drivers_json = excluded.drivers_json
            """, (
                name, comp_d["structural"]["score"], comp_d["dependency"]["score"],
                comp_d["transformation"]["score"], comp_d["data_model"]["score"],
                comp_d["semantic"]["score"], comp_d["customization"]["score"],
                comp_d["operational"]["score"], assessment["complexity_details"]["overall_complexity_score"],
                assessment["complexity"], json.dumps(assessment["complexity_details"]["primary_drivers"])
            )))

        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_writes(stmts)

        # Prioritize objects
        prioritization = self.prioritization_engine.prioritize_objects(results)

        return {
            "run_id": run_id,
            "system_id": system_id,
            "total_assessed": len(results),
            "results": results,
            "prioritization": prioritization
        }

    def assess_all_objects(self, system_id: str = "S21_LIVE") -> dict:
        return self.assess_all(system_id)

    def get_latest_assessment(self, object_name: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM assessment_findings
            WHERE object_name = ?
            ORDER BY id DESC LIMIT 1
        """, (object_name,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return self.assess_object(object_name)

        res = dict(row)
        res["findings"] = json.loads(res["findings_json"]) if res.get("findings_json") else {}
        return res

    def get_object_assessment(self, object_name: str) -> dict:
        return self.assess_object(object_name)

    def get_assessment_summary(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT f.*, o.type as object_type, f.overall_score as feasibility_score, f.recommended_target as target_recommendation
            FROM assessment_findings f
            LEFT JOIN bw_objects o ON f.object_name = o.technical_name
            WHERE f.assessment_run_id = (SELECT id FROM assessment_runs ORDER BY run_timestamp DESC LIMIT 1)
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not rows:
            # If no assessment run in DB yet, run assessment
            summary = self.assess_all("S21")
            return {
                "total_assessed": len(summary["results"]),
                "findings": summary["results"]
            }

        return {
            "total_assessed": len(rows),
            "findings": rows
        }

    def get_landscape_summary(self, filters: Optional[Dict[str, Any]] = None) -> dict:
        return self.landscape_engine.get_landscape_summary(filters)

    def get_prioritization_summary(self) -> dict:
        summary = self.assess_all()
        return summary.get("prioritization", {})
