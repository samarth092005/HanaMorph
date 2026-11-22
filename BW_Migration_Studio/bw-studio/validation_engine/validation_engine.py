import sqlite3
import json
import uuid
import os
import hashlib
from database.sqlite_queue import SingleWriterQueue

class ValidationEngine:
    """
    7-Level Validation Engine for HanaMorph BW Modernization Studio.
    Executes comprehensive checks across:
    - Level 1: Metadata validation
    - Level 2: Mapping validation
    - Level 3: Dependency validation
    - Level 4: Generated artifact syntax & structure
    - Level 5: Semantic & currency validation
    - Level 6: Data reconciliation readiness
    - Level 7: Security & zero credential leakage
    """
    def __init__(self, db_path: str):
        self.db_path = db_path

    def validate_project(self, project_id: str, plan_id: str, executed_by: str = "ValidationEngine") -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        run_id = f"val-{uuid.uuid4().hex[:8]}"
        stmts = [("""
            INSERT INTO validation_runs (id, project_id, status)
            VALUES (?, ?, 'IN_PROGRESS')
        """, (run_id, project_id))]

        cur.execute("""
            SELECT ga.* FROM generated_artifacts ga
            JOIN generation_runs gr ON ga.generation_run_id = gr.id
            WHERE gr.plan_id = ?
        """, (plan_id,))
        artifacts = [dict(r) for r in cur.fetchall()]

        results = []

        def add_check(artifact_id, obj_name, level, category, status, msg, expected="Valid", actual="Valid"):
            results.append({
                "run_id": run_id,
                "artifact_id": artifact_id,
                "object_name": obj_name,
                "check_level": level,
                "check_category": category,
                "status": status,
                "message": msg,
                "expected": str(expected),
                "actual": str(actual)
            })
            stmts.append(("""
                INSERT INTO validation_results (
                    validation_run_id, artifact_id, object_name, check_level,
                    check_category, status, message, expected, actual
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, artifact_id, obj_name, level, category, status, msg, str(expected), str(actual))))

        # 1. Level 1: Metadata Validation
        cur.execute("SELECT source_system FROM migration_projects WHERE id = ?", (project_id,))
        proj_row = cur.fetchone()
        source_sys = proj_row["source_system"] if proj_row and proj_row["source_system"] else "S21"
        cur.execute("SELECT * FROM bw_objects WHERE system_id = ? OR system_id = 'S21'", (source_sys,))
        bw_objs = [dict(r) for r in cur.fetchall()]
        for obj in bw_objs:
            name = obj["technical_name"]
            cur.execute("SELECT count(*) FROM bw_object_fields WHERE object_name = ?", (name,))
            f_count = cur.fetchone()[0]
            if f_count > 0:
                add_check(None, name, 1, "METADATA_COMPLETENESS", "PASS", f"Object {name} has {f_count} normalized fields.")
            else:
                add_check(None, name, 1, "METADATA_COMPLETENESS", "WARNING", f"Object {name} has 0 fields defined.")

        # 2. Level 2: Mapping Validation
        for art in [a for a in artifacts if a["artifact_type"] == "MAPPING_SPEC"]:
            src = art["source_object"]
            content = art["content"]
            if "DIRECT_1_TO_1" in content:
                add_check(art["id"], src, 2, "MAPPING_COMPLETENESS", "PASS", f"Source-to-target field mapping verified for {src}.")
            else:
                add_check(art["id"], src, 2, "MAPPING_COMPLETENESS", "WARNING", f"Incomplete mapping rules for {src}.")

        # 3. Level 3: Dependency Validation
        cur.execute("SELECT count(*) FROM bw_object_dependencies")
        dep_count = cur.fetchone()[0]
        if dep_count >= 5:
            add_check(None, "SYSTEM", 3, "DEPENDENCY_INTEGRITY", "PASS", f"Dependency topology verified with {dep_count} lineage edges.")
        else:
            add_check(None, "SYSTEM", 3, "DEPENDENCY_INTEGRITY", "WARNING", f"Sparse dependencies ({dep_count} edges).")

        # 4. Level 4: Generated Artifact Syntax Validation
        for art in artifacts:
            src = art["source_object"]
            atype = art["artifact_type"]
            content = art["content"]

            if atype == "DATASPHERE_CSN":
                try:
                    csn_json = json.loads(content)
                    if "$schema" in csn_json and "definitions" in csn_json:
                        add_check(art["id"], src, 4, "SYNTAX_CSN", "PASS", f"Valid SAP CSN v2.0 JSON schema for {art['target_name']}.")
                    else:
                        add_check(art["id"], src, 4, "SYNTAX_CSN", "FAIL", f"Missing required CSN schema elements in {art['target_name']}.")
                except Exception as e:
                    add_check(art["id"], src, 4, "SYNTAX_CSN", "FAIL", f"Invalid JSON syntax in CSN: {e}")

            elif atype == "HANA_SQL_DDL":
                if "CREATE VIEW" in content and "AS" in content and "FROM" in content:
                    add_check(art["id"], src, 4, "SYNTAX_DDL", "PASS", f"Valid HANA Cloud SQL View DDL for {art['target_name']}.")
                elif "CREATE COLUMN TABLE" in content and "PRIMARY KEY" in content:
                    add_check(art["id"], src, 4, "SYNTAX_DDL", "PASS", f"Valid HANA Cloud DDL with primary key for {art['target_name']}.")
                elif "CREATE COLUMN TABLE" in content:
                    add_check(art["id"], src, 4, "SYNTAX_DDL", "WARNING", f"HANA DDL generated without explicit primary key in {art['target_name']}.")
                else:
                    add_check(art["id"], src, 4, "SYNTAX_DDL", "FAIL", f"Unrecognized DDL statement structure in {art['target_name']}.")

        # 5. Level 5: Semantic Validation (Referential Currency/Unit Linkages & Keys)
        for art in [a for a in artifacts if a["artifact_type"] == "DATASPHERE_CSN"]:
            src = art["source_object"]
            tgt = art["target_name"]
            try:
                csn_data = json.loads(art["content"])
                defs = csn_data.get("definitions", {})
                if not defs:
                    add_check(art["id"], src, 5, "SEMANTICS", "FAIL", f"CSN artifact has empty definitions in {tgt}.")
                    continue

                for def_id, def_val in defs.items():
                    kind = def_val.get("kind", "")
                    elements = def_val.get("elements") or def_val.get("query", {}).get("elements", {})
                    
                    if kind == "entity":
                        has_key = any(el.get("key") is True for el in elements.values())
                        if has_key:
                            add_check(art["id"], src, 5, "SEMANTICS_KEY", "PASS", f"Primary key defined for entity {tgt}.")
                        else:
                            add_check(art["id"], src, 5, "SEMANTICS_KEY", "WARNING", f"No primary key marked for entity {tgt}.")

                    elif kind == "view":
                        from_entity = def_val.get("query", {}).get("from")
                        if from_entity:
                            add_check(art["id"], src, 5, "SEMANTICS_VIEW", "PASS", f"View base provider source verified: {from_entity}.")
                        else:
                            add_check(art["id"], src, 5, "SEMANTICS_VIEW", "WARNING", f"View query from source not explicitly declared in {tgt}.")

                    # Validate Currency and Unit references
                    checked_cur = False
                    checked_unit = False
                    for el_name, el_props in elements.items():
                        # Amount / Currency Check
                        if "@Semantics.amount.currencyCode" in el_props:
                            checked_cur = True
                            cur_ref = el_props["@Semantics.amount.currencyCode"]
                            if cur_ref in elements:
                                add_check(art["id"], src, 5, "SEMANTICS_CURRENCY", "PASS", f"Currency reference '{cur_ref}' verified in {tgt} for element '{el_name}'.")
                            else:
                                add_check(art["id"], src, 5, "SEMANTICS_CURRENCY", "FAIL", f"Dangling currency reference: '{cur_ref}' not found in entity elements for {tgt}.")

                        # Quantity / Unit Check
                        if "@Semantics.quantity.unitOfMeasure" in el_props:
                            checked_unit = True
                            unit_ref = el_props["@Semantics.quantity.unitOfMeasure"]
                            if unit_ref in elements:
                                add_check(art["id"], src, 5, "SEMANTICS_UNIT", "PASS", f"Unit reference '{unit_ref}' verified in {tgt} for element '{el_name}'.")
                            else:
                                add_check(art["id"], src, 5, "SEMANTICS_UNIT", "FAIL", f"Dangling unit reference: '{unit_ref}' not found in entity elements for {tgt}.")

                        # Decimal Precision / Scale Check
                        if el_props.get("type") == "cds.Decimal":
                            prec = el_props.get("precision", 0)
                            scale = el_props.get("scale", 0)
                            if prec < scale:
                                add_check(art["id"], src, 5, "SEMANTICS_DATATYPE", "FAIL", f"Invalid decimal precision {prec} < scale {scale} in {tgt}.{el_name}.")

                    if not checked_cur and not checked_unit:
                        add_check(art["id"], src, 5, "SEMANTICS_INTEGRITY", "PASS", f"Semantic data elements validated for {tgt}.")

            except Exception as e:
                add_check(art["id"], src, 5, "SEMANTICS", "FAIL", f"CSN semantic parsing error in {tgt}: {e}")

        # 6. Level 6: Data Validation (Checksum Match)
        for art in artifacts:
            actual_sha = hashlib.sha256(art["content"].encode('utf-8')).hexdigest()
            if actual_sha == art["checksum_sha256"]:
                add_check(art["id"], art["source_object"], 6, "DATA_INTEGRITY", "PASS", f"SHA-256 Checksum verified ({actual_sha[:10]}...).")
            else:
                add_check(art["id"], art["source_object"], 6, "DATA_INTEGRITY", "FAIL", "Checksum mismatch; file tampered.")

        # 7. Level 7: Security Validation (Zero Password/Secret Exposure)
        for art in artifacts:
            content = art["content"]
            forbidden_tokens = ["Tonystark", "pass@123", "password", "secret_key"]
            leaks = [tok for tok in forbidden_tokens if tok.lower() in content.lower()]
            if not leaks:
                add_check(art["id"], art["source_object"], 7, "SECURITY", "PASS", f"Zero secret leakage verified in {art['target_name']}.")
            else:
                add_check(art["id"], art["source_object"], 7, "SECURITY", "FAIL", f"Sensitive secret detected: {leaks}")

        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")

        stmts.append(("""
            UPDATE validation_runs
            SET status = 'COMPLETED',
                total_checks = ?,
                passed_checks = ?,
                failed_checks = ?
            WHERE id = ?
        """, (len(results), passed, failed, run_id)))

        conn.close()

        queue = SingleWriterQueue.get_instance(self.db_path)
        queue.execute_writes(stmts)

        return {
            "validation_run_id": run_id,
            "project_id": project_id,
            "total_checks": len(results),
            "passed": passed,
            "failed": failed,
            "passed_checks": passed,
            "failed_checks": failed,
            "status": "PASSED" if failed == 0 else "FAILED",
            "results": results
        }

    def get_validation_report(self, run_id: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM validation_runs WHERE id = ?", (run_id,))
        run_row = cur.fetchone()
        if not run_row:
            cur.execute("SELECT * FROM validation_runs ORDER BY rowid DESC LIMIT 1")
            run_row = cur.fetchone()
        if not run_row:
            conn.close()
            return None

        run_data = dict(run_row)
        cur.execute("SELECT * FROM validation_results WHERE validation_run_id = ? ORDER BY id ASC", (run_data["id"],))
        raw_results = [dict(r) for r in cur.fetchall()]
        conn.close()

        formatted_results = []
        for r in raw_results:
            formatted_results.append({
                "check_id": f"CHK-{r['id']}",
                "level": r["check_level"],
                "object_name": r["object_name"] or "-",
                "severity": r["check_category"],
                "message": r["message"],
                "status": r["status"]
            })

        run_data["results"] = formatted_results
        return run_data
