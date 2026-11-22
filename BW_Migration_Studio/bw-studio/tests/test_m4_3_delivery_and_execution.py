"""
HANAMORPH BW Migration & Modernization Studio
M4.3 Delivery, Validation, and Execution Readiness Test Suite
"""

import unittest
import os
import sys
import json
import tempfile
import shutil
import hashlib

# Ensure bw-studio root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deployment.package_validator import PackageValidator, PackageValidationResult
from deployment.runbook_generator import RunbookGenerator
from deployment.delivery_packager import DeliveryPackager
import cli

class TestM43DeliveryAndExecution(unittest.TestCase):

    def setUp(self):
        self.validator = PackageValidator()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "bw_studio.sqlite")
        self.runbook_gen = RunbookGenerator(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_mock_package(self, files_dict: dict) -> str:
        """Helper to create a temporary sealed package with manifest.json."""
        manifest = {
            "package_id": "pkg-test-01",
            "version": "1.0.0",
            "files": {}
        }
        for rel_path, content in files_dict.items():
            full_path = os.path.join(self.temp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            content_bytes = content.encode("utf-8")
            with open(full_path, "wb") as f:
                f.write(content_bytes)
            sha = hashlib.sha256(content_bytes).hexdigest()
            manifest["files"][rel_path] = {
                "size_bytes": len(content_bytes),
                "sha256": sha
            }

        manifest_path = os.path.join(self.temp_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return self.temp_dir

    # -------------------------------------------------------------
    # 1. Package Validator Tests
    # -------------------------------------------------------------
    def test_01_missing_manifest_fails_validation(self):
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir, exist_ok=True)
        res = self.validator.validate_package(empty_dir)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.manifest_verified)
        self.assertIn("manifest.json missing", res.corrupted_files)

    def test_02_valid_sealed_package_passes(self):
        csn_content = json.dumps({
            "$schema": "https://help.sap.com/doc/csn-v2.0.json",
            "definitions": {"SPACE.LT_SO": {"kind": "entity", "elements": {}}}
        })
        sql_content = "CREATE COLUMN TABLE \"SPACE\".\"LT_SO\" (\"ID\" NVARCHAR(10));"
        
        pkg_dir = self._create_mock_package({
            "generated-artifacts/LT_SO.csn.json": csn_content,
            "generated-artifacts/LT_SO.sql": sql_content
        })
        res = self.validator.validate_package(pkg_dir)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.manifest_verified)
        self.assertEqual(res.total_files_checked, 2)
        self.assertEqual(len(res.corrupted_files), 0)
        self.assertEqual(len(res.schema_errors), 0)
        self.assertEqual(len(res.security_findings), 0)

    def test_03_tampered_file_detected(self):
        sql_content = "CREATE COLUMN TABLE T1 (ID INT);"
        pkg_dir = self._create_mock_package({
            "generated-artifacts/T1.sql": sql_content
        })
        # Tamper file after manifest generation
        with open(os.path.join(pkg_dir, "generated-artifacts", "T1.sql"), "w", encoding="utf-8") as f:
            f.write("CREATE COLUMN TABLE T1_TAMPERED (ID INT);")

        res = self.validator.validate_package(pkg_dir)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.manifest_verified)
        self.assertEqual(len(res.corrupted_files), 1)
        self.assertIn("hash mismatch", res.corrupted_files[0])

    def test_04_credential_leak_detected(self):
        leaked_content = "-- Configuration\nPASSWORD = 'SecretSAPPassword123!';"
        pkg_dir = self._create_mock_package({
            "generated-artifacts/leaked.sql": leaked_content
        })
        res = self.validator.validate_package(pkg_dir)
        self.assertFalse(res.is_valid)
        self.assertEqual(len(res.security_findings), 1)
        self.assertIn("Potential credential leak", res.security_findings[0])

    def test_05_invalid_csn_schema_detected(self):
        bad_csn = json.dumps({"invalid_key": "no_schema"})
        pkg_dir = self._create_mock_package({
            "generated-artifacts/bad.csn.json": bad_csn
        })
        res = self.validator.validate_package(pkg_dir)
        self.assertFalse(res.is_valid)
        self.assertEqual(len(res.schema_errors), 1)
        self.assertIn("Missing required CSN keys", res.schema_errors[0]["error"])

    # -------------------------------------------------------------
    # 2. Runbook Generator Tests
    # -------------------------------------------------------------
    def test_06_runbook_generation_structure(self):
        rb = self.runbook_gen.generate_runbook(
            project_id="proj-test",
            plan_id="plan-test",
            space="FIN_SPACE"
        )
        self.assertEqual(rb["project_id"], "proj-test")
        self.assertEqual(rb["plan_id"], "plan-test")
        self.assertEqual(len(rb["phases"]), 5)
        self.assertIn("Phase 1: Prerequisites & Environment Readiness", rb["markdown_content"])
        self.assertIn("Phase 5: Post-Migration Data Reconciliation", rb["markdown_content"])
        self.assertIn("datasphere space show --space FIN_SPACE", rb["markdown_content"])

    # -------------------------------------------------------------
    # 3. CLI Subcommand Tests
    # -------------------------------------------------------------
    def test_07_cli_status(self):
        class MockArgs:
            pass
        code = cli.cmd_status(MockArgs())
        self.assertEqual(code, 0)

    def test_08_cli_runbook_command(self):
        class MockArgs:
            project_id = "proj-cli-test"
            plan_id = "plan-cli-test"
            space = "SALES_SPACE"
            output = os.path.join(self.temp_dir, "CLI_RUNBOOK.md")

        code = cli.cmd_runbook(MockArgs())
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(MockArgs.output))
        with open(MockArgs.output, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("SALES_SPACE", content)


if __name__ == "__main__":
    unittest.main()
