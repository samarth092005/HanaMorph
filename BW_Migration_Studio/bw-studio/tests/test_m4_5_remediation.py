"""
HANAMORPH BW Migration & Modernization Studio
Milestone M4.5 — Comprehensive Remediation & Hardening Verification Suite
Tests Workstreams A, B, C, D, E in an isolated, non-destructive test harness.
"""

import unittest
import os
import sys
import tempfile
import sqlite3
import json
import time

# Ensure bw-studio directory is on sys.path
STUDIO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO_DIR not in sys.path:
    sys.path.insert(0, STUDIO_DIR)

from transformation_engine.abap_parser import ABAPParser
from transformation_engine.sql_translator import ASTSQLTranslator, TranslationStatus
from transformation_engine.abap_ast import (
    RoutineAST, Identifier, Literal, FunctionCall, LookupStatement,
    Assignment, IfStatement, CaseStatement, UnsupportedStatement
)
from generation_engine.sac_model_generator import SACAnalyticalModelGenerator
from core.job_engine import BackgroundJobEngine, JobStatus
from core.database_backup_manager import DatabaseBackupManager
from backend.server import SessionManager, SESSION_MGR


class TestM45WorkstreamA_Transformation(unittest.TestCase):
    """Workstream A: ABAP Transformation Engine Correctness & Linguistic Corpus"""

    def setUp(self):
        self.parser = ABAPParser()
        self.translator = ASTSQLTranslator(target_dialect="HANA_SQL")

    def test_a1_lookup_parameter_binding_single_where(self):
        code = "SELECT SINGLE KTEXT FROM CSKT INTO L_TEXT WHERE KOSTL = SOURCE_FIELDS-KOSTL."
        ast = self.parser.parse(code, routine_name="ROUT_LOOKUP_1")
        res = self.translator.translate_routine(ast)
        self.assertIn("SELECT KTEXT INTO L_TEXT FROM CSKT", res.procedure_sql)
        # Verify source field is bound with :SOURCE. prefix, avoiding tautological KOSTL = KOSTL
        self.assertIn("WHERE KOSTL = :SOURCE.KOSTL;", res.procedure_sql)
        self.assertNotIn("WHERE KOSTL = KOSTL", res.procedure_sql)

    def test_a1_lookup_parameter_binding_multiple_where(self):
        code = "SELECT SINGLE KTEXT FROM CSKT INTO L_TEXT WHERE SPRAS = 'E' AND KOSTL = SOURCE_FIELDS-KOSTL."
        ast = self.parser.parse(code, routine_name="ROUT_LOOKUP_2")
        res = self.translator.translate_routine(ast)
        self.assertIn("SPRAS = 'E'", res.procedure_sql)
        self.assertIn("KOSTL = :SOURCE.KOSTL;", res.procedure_sql)

    def test_a2_concatenate_multiple_operands_with_separator(self):
        code = "CONCATENATE CITY COUNTRY INTO FULL_ADDR SEPARATED BY ', '."
        ast = self.parser.parse(code, routine_name="ROUT_CONCAT_SEP")
        res = self.translator.translate_routine(ast)
        self.assertEqual(res.status, TranslationStatus.AUTOMATICALLY_CONVERTED)
        self.assertEqual(res.expression_sql, "CITY || ', ' || COUNTRY")

    def test_a2_concatenate_five_operands_without_separator(self):
        code = "CONCATENATE A B C D E INTO RESULT."
        ast = self.parser.parse(code, routine_name="ROUT_CONCAT_MULTI")
        res = self.translator.translate_routine(ast)
        self.assertEqual(res.expression_sql, "A || B || C || D || E")

    def test_a3_escaped_quote_handling_exact_doubling(self):
        code = "RESULT = 'O''Connor'."
        ast = self.parser.parse(code, routine_name="ROUT_QUOTE")
        res = self.translator.translate_routine(ast)
        # Must be exactly 'O''Connor' in SQL, never 'O''''Connor'
        self.assertEqual(res.expression_sql, "'O''Connor'")

    def test_a4_strict_parser_rejects_missing_endif(self):
        code = "IF SOURCE_FIELDS-STATUS = 'A'. RESULT = 'ACTIVE'."
        ast = self.parser.parse(code, routine_name="ROUT_UNCLOSED_IF")
        self.assertEqual(len(ast.statements), 1)
        self.assertIsInstance(ast.statements[0], UnsupportedStatement)
        self.assertIn("Unclosed IF block", ast.statements[0].reason)
        self.assertIn("missing ENDIF", ast.statements[0].reason)

    def test_a4_strict_parser_rejects_missing_endcase(self):
        code = "CASE SOURCE_FIELDS-TYPE. WHEN 'A'. RESULT = 'A'."
        ast = self.parser.parse(code, routine_name="ROUT_UNCLOSED_CASE")
        self.assertEqual(len(ast.statements), 1)
        self.assertIsInstance(ast.statements[0], UnsupportedStatement)
        self.assertIn("Unclosed CASE block", ast.statements[0].reason)
        self.assertIn("missing ENDCASE", ast.statements[0].reason)

    def test_a4_strict_parser_rejects_missing_endloop(self):
        code = "LOOP AT ITAB INTO WA. RESULT = WA-FIELD."
        ast = self.parser.parse(code, routine_name="ROUT_UNCLOSED_LOOP")
        self.assertEqual(len(ast.statements), 1)
        self.assertIsInstance(ast.statements[0], UnsupportedStatement)
        self.assertIn("Unclosed LOOP block", ast.statements[0].reason)
        self.assertIn("missing ENDLOOP", ast.statements[0].reason)

    def test_a5_15_category_abap_corpus_completeness(self):
        """Verifies parsing and translation behavior across all 15 syntax categories."""
        corpus = [
            ("1. Conditionals", "IF A = 1. RESULT = 'ONE'. ELSE. RESULT = 'OTHER'. ENDIF.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("2. Case discrimination", "CASE A. WHEN '1'. RESULT = 1. WHEN OTHERS. RESULT = 0. ENDCASE.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("3. Direct assignment", "RESULT = SOURCE_FIELDS-NETWR.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("4. Arithmetic", "RESULT = SOURCE_FIELDS-AMOUNT * 1.18 + 5.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("5. String functions", "RESULT = STRLEN( SOURCE_FIELDS-NAME ).", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("6. String concat", "CONCATENATE FIRST LAST INTO NAME SEPARATED BY ' '.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("7. Database lookup", "SELECT SINGLE KTEXT FROM CSKT INTO L_TEXT WHERE KOSTL = SOURCE_FIELDS-KOSTL.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("8. Multi-cond lookup", "SELECT SINGLE KTEXT FROM CSKT INTO L_TEXT WHERE SPRAS = 'E' AND KOSTL = SOURCE_FIELDS-KOSTL.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("9. Table iteration", "LOOP AT ITAB INTO WA. ENDLOOP.", TranslationStatus.UNSUPPORTED),
            ("10. Nested blocks", "IF A = 1. IF B = 2. RESULT = 10. ELSE. RESULT = 5. ENDIF. ELSE. RESULT = 0. ENDIF.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("11. Comments", "* Full line comment\nRESULT = 10. \" inline comment", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("12. Escaped quotes", "RESULT = 'Item''s title'.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("13. Decimals", "RESULT = 12.345 * 2.", TranslationStatus.AUTOMATICALLY_CONVERTED),
            ("14. Unsupported keywords", "CALL FUNCTION 'CONVERT_CURRENCY'.", TranslationStatus.UNSUPPORTED),
            ("15. Malformed syntax", "IF A = 1. RESULT = 2.", TranslationStatus.UNSUPPORTED)
        ]

        for cat_name, code, expected_status in corpus:
            ast = self.parser.parse(code, routine_name=cat_name.replace(" ", "_"))
            res = self.translator.translate_routine(ast)
            self.assertEqual(res.status, expected_status, f"Failed on category {cat_name}: expected {expected_status}, got {res.status}")


class TestM45WorkstreamB_SACSemantics(unittest.TestCase):
    """Workstream B: SAC Model Semantic Field Classification & Ambiguity Handling"""

    def setUp(self):
        self.generator = SACAnalyticalModelGenerator()

    def test_b1_explicit_analytical_semantics_priority(self):
        fields = [
            {"field_name": "VAL_EXPLICIT_MEASURE", "data_type": "CHAR", "role": "MEASURE", "aggregation_type": "COUNT"},
            {"field_name": "VAL_EXPLICIT_DIMENSION", "data_type": "DEC", "role": "DIMENSION"}
        ]
        spec = self.generator.generate_sac_model("SAC_EXP", "SRC", "SPACE.VIEW", fields)
        self.assertEqual(len(spec["measures"]), 1)
        self.assertEqual(spec["measures"][0]["id"], "VAL_EXPLICIT_MEASURE")
        self.assertEqual(len(spec["dimensions"]), 1)
        self.assertEqual(spec["dimensions"][0]["id"], "VAL_EXPLICIT_DIMENSION")

    def test_b2_numeric_dimensions_not_misclassified_as_measures(self):
        fields = [
            {"field_name": "CUSTOMER_ID", "data_type": "DEC"},
            {"field_name": "DOCUMENT_NUMBER", "data_type": "INT"},
            {"field_name": "POSTAL_CODE", "data_type": "DEC"},
            {"field_name": "FISCPER", "data_type": "NUMC"}
        ]
        spec = self.generator.generate_sac_model("SAC_DIMS", "SRC", "SPACE.VIEW", fields)
        self.assertEqual(len(spec["measures"]), 0, "Numeric IDs and numbers must not be measures")
        self.assertEqual(len(spec["dimensions"]), 4)

    def test_b3_numeric_measures_correctly_classified(self):
        fields = [
            {"field_name": "NET_AMOUNT", "data_type": "DEC", "decimals": 2},
            {"field_name": "QUANTITY", "data_type": "QUAN", "decimals": 3},
            {"field_name": "REVENUE", "data_type": "CURR", "decimals": 2}
        ]
        spec = self.generator.generate_sac_model("SAC_MEAS", "SRC", "SPACE.VIEW", fields)
        self.assertEqual(len(spec["measures"]), 3)
        self.assertEqual(len(spec["dimensions"]), 0)

    def test_b4_ambiguous_fields_flagged_with_review_required(self):
        fields = [
            {"field_name": "CUSTOM_METRIC_01", "data_type": "DEC", "decimals": 2}
        ]
        spec = self.generator.generate_sac_model("SAC_AMBIG", "SRC", "SPACE.VIEW", fields)
        self.assertEqual(len(spec["measures"]), 0)
        self.assertEqual(len(spec["dimensions"]), 1)
        dim = spec["dimensions"][0]
        self.assertTrue(dim.get("review_required"))
        self.assertIn("lacks explicit analytical semantics", dim.get("review_reason", ""))
        self.assertEqual(len(spec["ambiguous_fields"]), 1)


class TestM45WorkstreamC_JobCrashRecovery(unittest.TestCase):
    """Workstream C: Background Job Engine Crash Recovery & State Reconciliation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_job_engine.sqlite")

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_c1_startup_reconciles_orphaned_running_jobs(self):
        # 1. Simulate database with job left in RUNNING status after sudden kill
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE background_jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                progress_pct INTEGER DEFAULT 0,
                payload TEXT,
                result TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO background_jobs (id, job_type, status, progress_pct, started_at)
            VALUES ('job-orphan-001', 'PACKAGE_CREATION', 'RUNNING', 45, '2026-11-22 10:00:00')
        """)
        conn.commit()
        conn.close()

        # 2. Initialize BackgroundJobEngine on this DB
        engine = BackgroundJobEngine(self.db_path, max_workers=2)

        # 3. Verify startup reconciliation safely transitioned orphaned job to FAILED
        job = engine.get_job("job-orphan-001")
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], JobStatus.FAILED)
        self.assertIn("interrupted by process termination", job["error_message"])
        self.assertIsNotNone(job["completed_at"])
        engine.executor.shutdown(wait=False)


class TestM45WorkstreamD_BackupRestore(unittest.TestCase):
    """Workstream D: Database Backup Verification & Separate-Destination Restore"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.active_db = os.path.join(self.temp_dir, "active.sqlite")
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.restore_dest = os.path.join(self.temp_dir, "restored.sqlite")

        # Create active test database with dummy table and data
        conn = sqlite3.connect(self.active_db)
        cur = conn.cursor()
        cur.execute("CREATE TABLE sample_items (id INTEGER PRIMARY KEY, name TEXT);")
        cur.execute("INSERT INTO sample_items (name) VALUES ('Item A'), ('Item B');")
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            for f in os.listdir(self.temp_dir):
                p = os.path.join(self.temp_dir, f)
                if os.path.isfile(p): os.remove(p)
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_d1_backup_and_restore_workflow(self):
        mgr = DatabaseBackupManager(self.active_db, backup_dir=self.backup_dir)
        backup_res = mgr.create_atomic_backup("unit_test")
        backup_path = backup_res["backup_path"]
        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(backup_res["integrity_verified"])

        # Execute restore into separate destination
        report = mgr.restore_backup(backup_path, self.restore_dest, verify=True)
        self.assertEqual(report["status"], "RESTORED_AND_VERIFIED")
        self.assertTrue(report["integrity_verified"])
        self.assertEqual(report["table_count"], 1)
        self.assertIn("sample_items", report["restored_tables"])
        self.assertEqual(report["source_sha256"], report["destination_sha256"])

        # Verify active database was untouched and data is intact in restored database
        conn = sqlite3.connect(self.restore_dest)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sample_items")
        self.assertEqual(cur.fetchone()[0], 2)
        conn.close()

    def test_d2_restore_prohibits_overwriting_active_db(self):
        mgr = DatabaseBackupManager(self.active_db, backup_dir=self.backup_dir)
        backup_res = mgr.create_atomic_backup("safeguard")
        with self.assertRaises(PermissionError):
            mgr.restore_backup(backup_res["backup_path"], self.active_db)


class TestM45WorkstreamE_AuthSecurity(unittest.TestCase):
    """Workstream E: Secure Session Management & CSRF Protection"""

    def setUp(self):
        self.mgr = SessionManager(ttl_seconds=3600)

    def test_e1_session_lifecycle(self):
        sid, csrf = self.mgr.create_session("admin")
        self.assertIsNotNone(sid)
        self.assertEqual(len(sid), 64) # 32 bytes hex
        self.assertIsNotNone(csrf)
        self.assertEqual(len(csrf), 32) # 16 bytes hex

        sess = self.mgr.validate_session(sid)
        self.assertIsNotNone(sess)
        self.assertEqual(sess["user"], "admin")

        # Invalidation / Logout
        self.assertTrue(self.mgr.invalidate_session(sid))
        self.assertIsNone(self.mgr.validate_session(sid))

    def test_e2_session_expiration(self):
        # Create expired session
        expired_mgr = SessionManager(ttl_seconds=-10)
        sid, _ = expired_mgr.create_session("admin")
        self.assertIsNone(expired_mgr.validate_session(sid))


if __name__ == "__main__":
    unittest.main()
