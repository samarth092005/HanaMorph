import sqlite3
import uuid
import json
import time
from database.sqlite_queue import SingleWriterQueue
from dependency_engine import DependencyGraph
from assessment_engine import AssessmentEngine

class PlanningEngine:
    """
    Dependency-aware SAP BW Migration Planning Engine.
    Converts assessment findings into sequenced, approval-gated migration plans.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.dep_graph = DependencyGraph(db_path)
        self.assessment_engine = AssessmentEngine(db_path)

    def create_project(self, project_name: str = None, name: str = None, description: str = None, source_system: str = "S21", target_platform: str = "SAP_DATASPHERE", target_space: str = "SALES_ANALYTICS", created_by: str = "Architect") -> dict:
        p_name = project_name or name or "BW Modernization Project"
        project_id = f"proj-{uuid.uuid4().hex[:8]}"
        queue = SingleWriterQueue.get_instance(self.db_path)

        queue.execute_write("""
            INSERT INTO migration_projects (id, project_name, source_system, target_platform, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (project_id, p_name, source_system, target_platform))

        return {
            "project_id": project_id,
            "project_name": p_name,
            "name": p_name,
            "source_system": source_system,
            "target_platform": target_platform,
            "target_space": target_space,
            "status": "ACTIVE"
        }

    def generate_plan(self, project_id: str, name: str = None, target_platform: str = None, selected_objects: list = None) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM migration_projects WHERE id = ?", (project_id,))
        proj = cur.fetchone()
        if not proj:
            conn.close()
            raise ValueError(f"Migration project '{project_id}' not found.")

        # Determine objects to plan
        if not selected_objects:
            cur.execute("SELECT technical_name FROM bw_objects WHERE system_id = ?", (proj["source_system"],))
            selected_objects = [r[0] for r in cur.fetchall()]

        # 1. Topological Sorting for Execution Sequence
        topo = self.dep_graph.get_topological_order(selected_objects)
        ordered_sequence = [n for n in topo["sequence"] if n in selected_objects]

        # 2. Determine Plan Version
        cur.execute("SELECT MAX(version) FROM migration_plans WHERE project_id = ?", (project_id,))
        latest_ver = cur.fetchone()[0] or 0
        new_ver = latest_ver + 1

        plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        stmts = [("""
            INSERT INTO migration_plans (id, project_id, version, status, created_at)
            VALUES (?, ?, ?, 'DRAFT', CURRENT_TIMESTAMP)
        """, (plan_id, project_id, new_ver))]

        plan_items = []
        for seq, obj_name in enumerate(ordered_sequence, 1):
            assessment = self.assessment_engine.get_latest_assessment(obj_name)
            rec_target = assessment["recommended_target"]
            complexity = assessment["complexity"]
            risk = assessment["risk_level"]

            if "Local Table" in rec_target:
                target_art = f"LT_{obj_name}"
                strategy = "AUTOMATED_CONVERSION"
            elif "Analytic Model" in rec_target:
                target_art = f"AM_{obj_name}"
                strategy = "AUTOMATED_CONVERSION_WITH_REVIEW"
            elif "Consumption View" in rec_target:
                target_art = f"CV_{obj_name}"
                strategy = "AUTOMATED_CONVERSION_WITH_REVIEW"
            elif "BW Bridge" in rec_target:
                target_art = f"BRIDGE_{obj_name}"
                strategy = "RETAIN_BW_BRIDGE"
            else:
                target_art = f"TGT_{obj_name}"
                strategy = "MANUAL_REDESIGN"

            stmts.append(("""
                INSERT INTO migration_plan_items (
                    plan_id, sequence_order, source_object, target_artifact,
                    target_platform, strategy, complexity, risk, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PLANNED')
            """, (plan_id, seq, obj_name, target_art, proj["target_platform"], strategy, complexity, risk)))

            plan_items.append({
                "sequence_order": seq,
                "source_object": obj_name,
                "target_artifact": target_art,
                "target_platform": proj["target_platform"],
                "strategy": strategy,
                "complexity": complexity,
                "risk": risk,
                "status": "PLANNED"
            })

        stmts.append(("""
            UPDATE migration_plans
            SET plan_json = ?
            WHERE id = ?
        """, (json.dumps(plan_items), plan_id)))

        conn.close()

        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_writes(stmts)

        return {
            "plan_id": plan_id,
            "project_id": project_id,
            "version": new_ver,
            "status": "DRAFT",
            "has_cycles": topo["has_cycle"],
            "cycles_detected": 1 if topo["has_cycle"] else 0,
            "total_items": len(plan_items),
            "plan_items": plan_items
        }

    def approve_plan(self, plan_id: str, approver: str = "Lead Migration Architect", notes: str = "") -> dict:
        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_write("""
            UPDATE migration_plans
            SET status = 'APPROVED',
                approved_by = ?,
                approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (approver, plan_id))

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT project_id, version FROM migration_plans WHERE id = ?", (plan_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            raise ValueError(f"Plan '{plan_id}' not found.")

        return {
            "plan_id": plan_id,
            "project_id": row[0],
            "version": row[1],
            "status": "APPROVED",
            "approved_by": approver
        }

    def get_plan(self, plan_id: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM migration_plans WHERE id = ?", (plan_id,))
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT * FROM migration_plans ORDER BY rowid DESC LIMIT 1")
            row = cur.fetchone()
        if not row:
            conn.close()
            return None

        res = dict(row)
        cur.execute("SELECT * FROM migration_plan_items WHERE plan_id = ? ORDER BY sequence_order ASC", (res["id"],))
        res["items"] = [dict(r) for r in cur.fetchall()]
        conn.close()
        return res

    def get_plan_details(self, plan_id: str) -> dict:
        return self.get_plan(plan_id)

    def get_latest_approved_plan(self, project_id: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM migration_plans
            WHERE project_id = ? AND status = 'APPROVED'
            ORDER BY version DESC LIMIT 1
        """, (project_id,))
        row = cur.fetchone()
        if not row:
            # Fallback to latest draft if none approved
            cur.execute("""
                SELECT * FROM migration_plans
                WHERE project_id = ?
                ORDER BY version DESC LIMIT 1
            """, (project_id,))
            row = cur.fetchone()

        if not row:
            conn.close()
            return None

        res = dict(row)
        cur.execute("SELECT * FROM migration_plan_items WHERE plan_id = ? ORDER BY sequence_order ASC", (res["id"],))
        res["items"] = [dict(r) for r in cur.fetchall()]
        conn.close()
        return res

    def list_projects(self) -> list:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM migration_projects ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
