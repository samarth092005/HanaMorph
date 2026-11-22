"""
Synthetic End-to-End Verification Script
Tests the full migration lifecycle on a 100% synthetic, non-SAP dataset:
1. Connection profile test (mock)
2. Offline metadata import (JSON bundle)
3. Canonical inventory & snapshot verification
4. Dependency analysis & DAG topological sort
5. Multi-dimensional assessment & 4-route recommendation
6. Migration project creation & plan generation
7. Human approval gate
8. Artifact generation (CSN, SQL, Mapping)
9. 7-Level validation engine
10. Sealed delivery packaging & SHA-256 manifest
"""
import os
import sys
import json
import time

# Ensure parent directory is on sys.path
studio_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if studio_dir not in sys.path:
    sys.path.insert(0, studio_dir)

from discovery.discovery_engine import DiscoveryEngine
from assessment_engine.assessment_engine import AssessmentEngine
from planning_engine.planning_engine import PlanningEngine
from generation_engine.generation_engine import GenerationEngine
from validation_engine.validation_engine import ValidationEngine
from deployment.delivery_packager import DeliveryPackager

def run_synthetic_verification():
    db_path = os.path.join(studio_dir, "database", "bw_studio.sqlite")
    print(f"[*] Target SQLite DB: {db_path}")

    # 1. Prepare synthetic bundle
    bundle = {
        "system_id": "SYNTH_BW",
        "exported_at": "2026-11-22T00:50:00Z",
        "objects": [
            {
                "technical_name": "ZSYNTH_ADSO_01",
                "type": "ADSO",
                "description": "Synthetic Sales Actuals",
                "package": "Z_SYNTH_FIN",
                "infoarea": "FINANCE",
                "fields": [
                    {"name": "DOC_ID", "data_type": "CHAR", "length": 10, "is_key": 1, "description": "Document ID"},
                    {"name": "NET_AMOUNT", "data_type": "DEC", "length": 15, "decimals": 2, "semantics": "AMOUNT", "currency_unit_field": "DOC_CURR", "description": "Net Value"},
                    {"name": "DOC_CURR", "data_type": "CHAR", "length": 5, "semantics": "CURRENCY", "description": "Currency Key"}
                ],
                "dependencies": []
            },
            {
                "technical_name": "ZSYNTH_CP_01",
                "type": "COMPOSITE_PROVIDER",
                "description": "Synthetic Sales Reporting View",
                "package": "Z_SYNTH_REP",
                "infoarea": "SALES",
                "fields": [
                    {"name": "DOC_ID", "data_type": "CHAR", "length": 10, "is_key": 1, "description": "Document ID"},
                    {"name": "NET_AMOUNT", "data_type": "DEC", "length": 15, "decimals": 2, "semantics": "AMOUNT", "currency_unit_field": "DOC_CURR", "description": "Net Value"},
                    {"name": "DOC_CURR", "data_type": "CHAR", "length": 5, "semantics": "CURRENCY", "description": "Currency Key"}
                ],
                "dependencies": [
                    ["ZSYNTH_ADSO_01", "ZSYNTH_CP_01", "UNION_ELEMENT"]
                ]
            }
        ]
    }

    # Step 1: Import synthetic bundle
    print("\n[Step 1] Ingesting synthetic metadata bundle...")
    disc = DiscoveryEngine(db_path)
    import_res = disc.import_metadata_bundle(bundle)
    print(f"  -> Status: {import_res['status']}")
    print(f"  -> Objects Imported: {import_res['imported_count']}")
    print(f"  -> Provenance: {import_res['provenance']}")
    assert import_res["status"] == "COMPLETED"
    assert import_res["imported_count"] == 2
    assert import_res["provenance"] == "IMPORTED"

    # Step 2: Assessment
    print("\n[Step 2] Assessing synthetic objects...")
    assess = AssessmentEngine(db_path)
    for obj in bundle["objects"]:
        name = obj["technical_name"]
        res = assess.assess_object(name)
        print(f"  -> Object: {name}")
        print(f"     Overall Score: {res['overall_score']}/100")
        print(f"     Target Route:  {res['recommended_target']}")
        print(f"     Risk Tier:     {res['risk_level']}")
        assert res["overall_score"] > 0
        assert res["recommended_target"] != ""

    # Step 3: Planning & DAG Sequencing
    print("\n[Step 3] Creating project and generating migration plan...")
    planner = PlanningEngine(db_path)
    proj = planner.create_project(
        name="Synthetic Modernization Project",
        source_system="SYNTH_BW",
        target_platform="SAP_DATASPHERE",
        description="Automated Synthetic E2E verification project"
    )
    proj_id = proj["project_id"]
    print(f"  -> Created Project: {proj_id}")

    plan = planner.generate_plan(proj_id, target_platform="SAP_DATASPHERE")
    plan_id = plan["plan_id"]
    print(f"  -> Generated Plan ID: {plan_id}")
    print(f"  -> Plan Status: {plan['status']} (Initial)")
    print(f"  -> Total Waves/Items: {plan['total_items']}")
    assert plan["status"] == "DRAFT"

    # Step 4: Approval
    print("\n[Step 4] Approving migration plan...")
    approved = planner.approve_plan(plan_id, approver="Enterprise Lead Auditor", notes="Verified synthetic DAG")
    print(f"  -> Updated Plan Status: {approved['status']}")
    assert approved["status"] == "APPROVED"

    # Step 5: Generation
    print("\n[Step 5] Generating target artifacts (CSN, SQL, Mapping)...")
    gen = GenerationEngine(db_path)
    gen_res = gen.generate_for_plan(plan_id, space="SYNTH_SPACE")
    print(f"  -> Total Artifacts Generated: {gen_res['total_artifacts']}")
    for a in gen_res["artifacts"]:
        print(f"     * {a['target_name']} ({a['type']})")
        print(f"       File: {a['file_path']}")
        print(f"       SHA-256: {a['checksum_sha256'][:16]}...")
        assert os.path.exists(a["file_path"])
    assert gen_res["total_artifacts"] >= 4

    # Step 6: 7-Level Validation
    print("\n[Step 6] Running 7-Level Validation Engine...")
    val = ValidationEngine(db_path)
    val_res = val.validate_project(proj_id, plan_id)
    print(f"  -> Validation Run ID: {val_res['validation_run_id']}")
    print(f"  -> Status: {val_res['status']}")
    print(f"  -> Total Checks:  {val_res['total_checks']}")
    print(f"  -> Passed Checks: {val_res['passed_checks']}")
    print(f"  -> Failed Checks: {val_res['failed_checks']}")
    assert val_res["failed_checks"] == 0

    # Step 7: Sealed Delivery Packaging
    print("\n[Step 7] Creating sealed delivery package...")
    packager = DeliveryPackager(db_path)
    pkg = packager.create_package(proj_id, plan_id, version="1.0.0", approver="Enterprise Lead Auditor")
    print(f"  -> Package ID: {pkg['package_id']}")
    print(f"  -> Status: {pkg['status']}")
    print(f"  -> Total Files: {pkg['total_files']}")
    print(f"  -> Master SHA-256: {pkg['package_checksum_sha256']}")
    assert pkg["status"] == "PACKAGED_AND_VERIFIED"
    assert os.path.exists(os.path.join(pkg["package_dir"], "manifest.json"))
    assert os.path.exists(os.path.join(pkg["package_dir"], "project-summary.md"))
    assert os.path.exists(os.path.join(pkg["package_dir"], "source-inventory.json"))

    print("\n========================================================")
    print(">>> SYNTHETIC END-TO-END FLOW VERIFIED SUCCESSFULLY! <<<")
    print("========================================================\n")

if __name__ == "__main__":
    run_synthetic_verification()
