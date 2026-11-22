import unittest
import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from discovery.discovery_engine import DiscoveryEngine
from assessment_engine.assessment_engine import AssessmentEngine
from planning_engine.planning_engine import PlanningEngine
from generation_engine.generation_engine import GenerationEngine
from validation_engine.validation_engine import ValidationEngine
from deployment.delivery_packager import DeliveryPackager

DB_PATH = os.path.join(BASE_DIR, "database", "bw_studio.sqlite")
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "output")
DELIVERY_DIR = os.path.join(os.path.dirname(BASE_DIR), "delivery")


class TestEndToEndEngines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = DB_PATH
        cls.output_dir = OUTPUT_DIR
        cls.delivery_dir = DELIVERY_DIR

    def test_01_discovery_engine_catalog_and_lineage(self):
        engine = DiscoveryEngine(self.db_path)
        catalog = engine.get_catalog()
        self.assertIsInstance(catalog, list)
        self.assertGreaterEqual(len(catalog), 5)
        
        # Verify ZSAM_SO01 exists and has verified fields
        so01 = next((o for o in catalog if o["name"] == "ZSAM_SO01"), None)
        self.assertIsNotNone(so01)
        self.assertGreater(so01["field_count"], 0)

        # Lineage graph verification
        lineage = engine.get_lineage_graph()
        self.assertIn("nodes", lineage)
        self.assertIn("edges", lineage)
        self.assertGreaterEqual(len(lineage["nodes"]), 5)

    def test_02_assessment_engine_weighted_scoring(self):
        engine = AssessmentEngine(self.db_path)
        so01_eval = engine.assess_object("ZSAM_SO01")
        self.assertIn("recommended_target", so01_eval)
        self.assertIn("Native Datasphere", so01_eval["recommended_target"])
        self.assertGreaterEqual(so01_eval["overall_score"], 80)
        self.assertEqual(so01_eval["risk_level"], "LOW")

        # Verify ABAP routine detection triggers Bridge recommendation
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT technical_name FROM bw_objects WHERE technical_name LIKE '%GL%' OR technical_name LIKE '%ABAP%'")
        abap_obj = cur.fetchone()
        conn.close()

        if abap_obj:
            abap_eval = engine.assess_object(abap_obj[0])
            self.assertEqual(abap_eval["recommended_target"], "SAP BW Bridge")

    def test_03_planning_engine_dag_and_approval(self):
        engine = PlanningEngine(self.db_path)
        proj = engine.create_project(
            name="CI Test Project",
            description="Automated project for integration testing",
            target_space="TEST_SPACE",
            created_by="CI_Runner"
        )
        self.assertTrue(proj["project_id"].startswith("proj-"))

        plan = engine.generate_plan(
            project_id=proj["project_id"],
            name="CI Test Plan",
            target_platform="Native Datasphere"
        )
        self.assertTrue(plan["plan_id"].startswith("plan-"))
        self.assertEqual(plan["status"], "DRAFT")
        self.assertEqual(plan["cycles_detected"], 0)
        self.assertGreaterEqual(plan["total_items"], 5)

        # Gating check: Cannot generate artifacts while DRAFT
        gen_engine = GenerationEngine(self.db_path, self.output_dir)
        with self.assertRaises(ValueError):
            gen_engine.generate_for_plan(plan["plan_id"])

        # Approve plan
        approved = engine.approve_plan(plan["plan_id"], "Test Architect", "CI Approval")
        self.assertEqual(approved["status"], "APPROVED")

    def test_04_generation_engine_csn_and_ddl(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id FROM migration_plans WHERE status = 'APPROVED' ORDER BY id DESC LIMIT 1")
        plan_row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(plan_row)
        plan_id = plan_row[0]
        gen_engine = GenerationEngine(self.db_path, self.output_dir)
        gen_res = gen_engine.generate_for_plan(plan_id)
        self.assertGreaterEqual(gen_res["total_artifacts"], 10)
        
        artifacts = gen_engine.get_generation_artifacts(plan_id)
        self.assertGreaterEqual(len(artifacts), 10)
        
        # Verify SHA-256 exists for all artifacts
        for a in artifacts:
            sha = a.get("checksum_sha256") or a.get("sha256")
            self.assertIsNotNone(sha)
            self.assertEqual(len(sha), 64)

    def test_05_validation_engine_7_levels(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, project_id FROM migration_plans WHERE status = 'APPROVED' ORDER BY id DESC LIMIT 1")
        plan_row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(plan_row)
        plan_id, project_id = plan_row[0], plan_row[1]
        val_engine = ValidationEngine(self.db_path)
        res = val_engine.validate_project(project_id, plan_id, "CI_Validator")
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["failed_checks"], 0)
        self.assertGreaterEqual(res["passed_checks"], 10)

    def test_06_delivery_packager_manifest_sealing(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, project_id FROM migration_plans WHERE status = 'APPROVED' ORDER BY id DESC LIMIT 1")
        plan_row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(plan_row)
        plan_id, project_id = plan_row[0], plan_row[1]
        packager = DeliveryPackager(self.db_path, self.output_dir, self.delivery_dir)
        pkg = packager.create_package(project_id, plan_id, "CI_Packager")
        self.assertTrue(pkg["package_id"].startswith("pkg-"))
        self.assertGreaterEqual(pkg["total_files"], 5)
        
        # Verify manifest.json exists and contains correct metadata
        manifest = packager.get_package_manifest(pkg["package_id"])
        self.assertEqual(manifest["package_id"], pkg["package_id"])
        self.assertTrue(manifest["summary"]["validation_passed"])
        self.assertGreater(len(manifest["files"]), 0)


if __name__ == "__main__":
    unittest.main()
