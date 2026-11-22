import sqlite3
import hashlib
import json
import uuid
import os
import time
from database.sqlite_queue import SingleWriterQueue
from .csn_generator import DatasphereCSNGenerator
from .hana_ddl_generator import HANASQLGenerator
from .mapping_generator import MappingSpecGenerator
from .replication_flow_generator import DatasphereReplicationFlowGenerator
from .sac_model_generator import SACAnalyticalModelGenerator

class GenerationEngine:
    """
    Modular Code and Artifact Generation Engine for SAP Datasphere, HANA Cloud, and SAC.
    Generates deterministic, traceable, checksummed artifacts locally with full provenance tracking.
    Milestone M4.2
    """
    def __init__(self, db_path: str, output_base_dir: str = None):
        self.db_path = db_path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.output_base_dir = output_base_dir or os.path.join(base_dir, "output")
        self.csn_gen = DatasphereCSNGenerator()
        self.ddl_gen = HANASQLGenerator()
        self.map_gen = MappingSpecGenerator()
        self.repl_gen = DatasphereReplicationFlowGenerator()
        self.sac_gen = SACAnalyticalModelGenerator()

    def generate_for_plan(self, plan_id: str, space: str = "SALES_ANALYTICS") -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM migration_plans WHERE id = ?", (plan_id,))
        plan = cur.fetchone()
        if not plan:
            conn.close()
            raise ValueError(f"Migration plan '{plan_id}' not found.")

        if plan["status"] != "APPROVED":
            conn.close()
            raise ValueError(f"Migration plan '{plan_id}' is in status '{plan['status']}'. Explicit approval is required before code generation.")

        cur.execute("SELECT * FROM migration_plan_items WHERE plan_id = ? ORDER BY sequence_order ASC", (plan_id,))
        items = [dict(r) for r in cur.fetchall()]

        run_id = f"gen-{uuid.uuid4().hex[:8]}"
        project_dir = os.path.join(self.output_base_dir, plan["project_id"], plan_id)
        os.makedirs(project_dir, exist_ok=True)

        stmts = [("""
            INSERT INTO generation_runs (id, plan_id, target_platform, status, started_at, total_artifacts)
            VALUES (?, ?, 'SAP_DATASPHERE', 'IN_PROGRESS', CURRENT_TIMESTAMP, 0)
        """, (run_id, plan_id))]

        generated_list = []

        for item in items:
            src_obj = item["source_object"]
            tgt_name = item["target_artifact"]

            # Determine source object type and metadata
            cur.execute("SELECT type, description FROM bw_objects WHERE technical_name = ?", (src_obj,))
            obj_row = cur.fetchone()
            if not obj_row:
                cur.execute("SELECT type, description FROM source_catalog WHERE name = ?", (src_obj,))
                obj_row = cur.fetchone()
            obj_type = (obj_row[0] if obj_row else "ADSO").upper()
            obj_desc = obj_row[1] if obj_row else f"Migrated from {src_obj}"

            source_urn = f"urn:hanamorph:bw:s21:{obj_type.lower()}:{src_obj}"

            # Fetch object fields
            cur.execute("SELECT * FROM bw_object_fields WHERE object_name = ? ORDER BY is_key DESC, field_name ASC", (src_obj,))
            fields = [dict(f) for f in cur.fetchall()]
            if not fields:
                # Default minimal fields if not populated
                fields = [{"field_name": "ID", "data_type": "CHAR", "length": 10, "is_key": 1}]

            # Determine base entity for view-based artifacts
            cur.execute("SELECT source_object FROM bw_object_dependencies WHERE dependent_object = ? LIMIT 1", (src_obj,))
            dep_row = cur.fetchone()
            base_src = dep_row[0] if dep_row else "ZSAM_SO01"
            base_entity = f"LT_{base_src}"

            # Object-Semantic Generation Routing
            is_view_semantic = (
                obj_type in ["COMPOSITE_PROVIDER", "BW_QUERY", "INFOSOURCE"] or
                tgt_name.startswith("AM_") or tgt_name.startswith("CV_") or tgt_name.startswith("TV_")
            )

            if is_view_semantic:
                if obj_type == "COMPOSITE_PROVIDER" or tgt_name.startswith("AM_"):
                    csn_dict = self.csn_gen.generate_view_csn(space, tgt_name, base_entity, fields, f"Analytic View for {src_obj}")
                    ddl_str = self.ddl_gen.generate_sql_view_ddl(space, tgt_name, base_entity, fields)
                    gen_status = "GENERATED"
                elif obj_type == "BW_QUERY" or tgt_name.startswith("CV_"):
                    csn_dict = self.csn_gen.generate_view_csn(space, tgt_name, base_entity, fields, f"Consumption View for {src_obj}")
                    ddl_str = self.ddl_gen.generate_sql_view_ddl(space, tgt_name, base_entity, fields)
                    gen_status = "GENERATED_WITH_WARNINGS" if len(fields) <= 1 else "GENERATED"
                else:
                    csn_dict = self.csn_gen.generate_view_csn(space, tgt_name, base_entity, fields, f"Transformation View for {src_obj}")
                    ddl_str = self.ddl_gen.generate_sql_view_ddl(space, tgt_name, base_entity, fields)
                    gen_status = "GENERATED"
            else:
                # Physical Local Table for ADSO
                csn_dict = self.csn_gen.generate_entity_csn(space, tgt_name, fields, f"Local Table for {src_obj}")
                ddl_str = self.ddl_gen.generate_column_table_ddl(space, tgt_name, fields)
                gen_status = "GENERATED"

            # 1. Generate CSN Definition
            csn_str = json.dumps(csn_dict, indent=2)
            csn_sha = hashlib.sha256(csn_str.encode('utf-8')).hexdigest()
            csn_path = os.path.join(project_dir, f"{tgt_name}.csn.json")
            with open(csn_path, "w", encoding="utf-8") as f:
                f.write(csn_str)

            art_id_csn = f"art-{uuid.uuid4().hex[:8]}"
            stmts.append(("""
                INSERT INTO generated_artifacts (id, generation_run_id, source_object, target_name, artifact_type, file_path, content, checksum_sha256, validation_status)
                VALUES (?, ?, ?, ?, 'DATASPHERE_CSN', ?, ?, ?, ?)
            """, (art_id_csn, run_id, src_obj, tgt_name, csn_path, csn_str, csn_sha, gen_status)))

            generated_list.append({
                "artifact_id": art_id_csn,
                "source_object": src_obj,
                "source_urn": source_urn,
                "target_name": tgt_name,
                "type": "DATASPHERE_CSN",
                "semantic_kind": "view" if is_view_semantic else "entity",
                "file_path": csn_path,
                "checksum_sha256": csn_sha,
                "generation_status": gen_status
            })

            # 2. Generate HANA Cloud DDL
            ddl_sha = hashlib.sha256(ddl_str.encode('utf-8')).hexdigest()
            ddl_path = os.path.join(project_dir, f"{tgt_name}.sql")
            with open(ddl_path, "w", encoding="utf-8") as f:
                f.write(ddl_str)

            art_id_ddl = f"art-{uuid.uuid4().hex[:8]}"
            stmts.append(("""
                INSERT INTO generated_artifacts (id, generation_run_id, source_object, target_name, artifact_type, file_path, content, checksum_sha256, validation_status)
                VALUES (?, ?, ?, ?, 'HANA_SQL_DDL', ?, ?, ?, ?)
            """, (art_id_ddl, run_id, src_obj, tgt_name, ddl_path, ddl_str, ddl_sha, gen_status)))

            generated_list.append({
                "artifact_id": art_id_ddl,
                "source_object": src_obj,
                "source_urn": source_urn,
                "target_name": tgt_name,
                "type": "HANA_SQL_DDL",
                "semantic_kind": "view" if is_view_semantic else "entity",
                "file_path": ddl_path,
                "checksum_sha256": ddl_sha,
                "generation_status": gen_status
            })

            # 3. Generate Mapping Specification
            map_str = self.map_gen.generate_mapping_markdown(src_obj, tgt_name, fields)
            map_sha = hashlib.sha256(map_str.encode('utf-8')).hexdigest()
            map_path = os.path.join(project_dir, f"{tgt_name}_mapping.md")
            with open(map_path, "w", encoding="utf-8") as f:
                f.write(map_str)

            art_id_map = f"art-{uuid.uuid4().hex[:8]}"
            stmts.append(("""
                INSERT INTO generated_artifacts (id, generation_run_id, source_object, target_name, artifact_type, file_path, content, checksum_sha256, validation_status)
                VALUES (?, ?, ?, ?, 'MAPPING_SPEC', ?, ?, ?, 'GENERATED')
            """, (art_id_map, run_id, src_obj, tgt_name, map_path, map_str, map_sha)))

            generated_list.append({
                "artifact_id": art_id_map,
                "source_object": src_obj,
                "source_urn": source_urn,
                "target_name": tgt_name,
                "type": "MAPPING_SPEC",
                "file_path": map_path,
                "checksum_sha256": map_sha
            })

            # 4. Generate Datasphere Replication Flow (for physical storage / staging entities)
            if not is_view_semantic or obj_type in ["ADSO", "INFOCUBE"]:
                repl_spec = self.repl_gen.generate_replication_flow(
                    space=space,
                    source_object=src_obj,
                    target_name=tgt_name,
                    fields=fields,
                    source_urn=source_urn
                )
                repl_str = json.dumps(repl_spec, indent=2)
                repl_sha = hashlib.sha256(repl_str.encode("utf-8")).hexdigest()
                repl_path = os.path.join(project_dir, f"{tgt_name}_repl_flow.json")
                with open(repl_path, "w", encoding="utf-8") as f:
                    f.write(repl_str)

                art_id_repl = f"art-{uuid.uuid4().hex[:8]}"
                stmts.append(("""
                    INSERT INTO generated_artifacts (id, generation_run_id, source_object, target_name, artifact_type, file_path, content, checksum_sha256, validation_status)
                    VALUES (?, ?, ?, ?, 'DATASPHERE_REPLICATION_FLOW', ?, ?, ?, 'GENERATED')
                """, (art_id_repl, run_id, src_obj, tgt_name, repl_path, repl_str, repl_sha)))

                generated_list.append({
                    "artifact_id": art_id_repl,
                    "source_object": src_obj,
                    "source_urn": source_urn,
                    "target_name": tgt_name,
                    "type": "DATASPHERE_REPLICATION_FLOW",
                    "file_path": repl_path,
                    "checksum_sha256": repl_sha
                })

            # 5. Generate SAC Analytical Model (for analytical views / queries / CompositeProviders)
            if is_view_semantic or obj_type in ["COMPOSITE_PROVIDER", "BW_QUERY"]:
                sac_spec = self.sac_gen.generate_sac_model(
                    model_name=f"SAC_{tgt_name}",
                    source_object=src_obj,
                    base_view_id=f"{space}.{tgt_name}",
                    fields=fields,
                    description=obj_desc,
                    source_urn=source_urn
                )
                sac_str = json.dumps(sac_spec, indent=2)
                sac_sha = hashlib.sha256(sac_str.encode("utf-8")).hexdigest()
                sac_path = os.path.join(project_dir, f"SAC_{tgt_name}_model.json")
                with open(sac_path, "w", encoding="utf-8") as f:
                    f.write(sac_str)

                art_id_sac = f"art-{uuid.uuid4().hex[:8]}"
                stmts.append(("""
                    INSERT INTO generated_artifacts (id, generation_run_id, source_object, target_name, artifact_type, file_path, content, checksum_sha256, validation_status)
                    VALUES (?, ?, ?, ?, 'SAC_ANALYTIC_MODEL', ?, ?, ?, 'GENERATED')
                """, (art_id_sac, run_id, src_obj, tgt_name, sac_path, sac_str, sac_sha)))

                generated_list.append({
                    "artifact_id": art_id_sac,
                    "source_object": src_obj,
                    "source_urn": source_urn,
                    "target_name": tgt_name,
                    "type": "SAC_ANALYTIC_MODEL",
                    "file_path": sac_path,
                    "checksum_sha256": sac_sha
                })

        stmts.append(("""
            UPDATE generation_runs
            SET status = 'COMPLETED',
                completed_at = CURRENT_TIMESTAMP,
                total_artifacts = ?
            WHERE id = ?
        """, (len(generated_list), run_id)))

        conn.close()

        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_writes(stmts)

        return {
            "run_id": run_id,
            "plan_id": plan_id,
            "project_dir": project_dir,
            "total_artifacts": len(generated_list),
            "artifacts": generated_list
        }

    def list_artifacts_for_plan(self, plan_id: str) -> list:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT ga.* FROM generated_artifacts ga
            JOIN generation_runs gr ON ga.generation_run_id = gr.id
            WHERE gr.plan_id = ?
            ORDER BY ga.created_at DESC
        """, (plan_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_generation_artifacts(self, plan_id: str) -> list:
        return self.list_artifacts_for_plan(plan_id)
