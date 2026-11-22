#!/usr/bin/env python3
"""
HANAMORPH BW Migration & Modernization Studio
Unified Standalone Command Line Interface (CLI)
Milestone M4.3
"""

import sys
import os
import argparse
import json
import sqlite3

# Ensure bw-studio directory is in Python path
STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
if STUDIO_DIR not in sys.path:
    sys.path.insert(0, STUDIO_DIR)

from assessment_engine.assessment_engine import AssessmentEngine
from generation_engine.generation_engine import GenerationEngine
from deployment.delivery_packager import DeliveryPackager
from deployment.package_validator import PackageValidator
from deployment.runbook_generator import RunbookGenerator
from core.database_backup_manager import DatabaseBackupManager

DB_PATH = os.path.join(STUDIO_DIR, "database", "bw_studio.sqlite")

def get_db_path():
    return os.environ.get("BW_STUDIO_DB_PATH", DB_PATH)

def cmd_status(args):
    """Prints database, configuration, and security status."""
    db_path = get_db_path()
    exists = os.path.exists(db_path)
    size_kb = os.path.getsize(db_path) / 1024 if exists else 0

    print("=" * 60)
    print("HANAMORPH BW MIGRATION STUDIO - SYSTEM STATUS")
    print("=" * 60)
    print(f"Application Root:  {STUDIO_DIR}")
    print(f"Database File:     {db_path}")
    print(f"Database Exists:   {exists} ({size_kb:.1f} KB)")
    print(f"SAP Source System: {os.environ.get('SAP_BW_SYSTEM_ID', 'S21')} (Client {os.environ.get('SAP_BW_CLIENT', '200')})")
    print(f"Read-Only Guard:   {os.environ.get('SAP_BW_STRICT_READ_ONLY', 'true')} (Active)")
    print(f"API Auth Key Set:  {bool(os.environ.get('BW_STUDIO_API_KEY'))}")

    if exists:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
            tbl_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM bw_objects")
            obj_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM migration_plans")
            plan_count = cur.fetchone()[0]
            conn.close()
            print(f"Total Tables:      {tbl_count}")
            print(f"Discovered Objects:{obj_count}")
            print(f"Migration Plans:   {plan_count}")
        except Exception as e:
            print(f"DB Query Warning:  {e}")
    print("=" * 60)
    return 0

def cmd_assess(args):
    """Runs modernization assessment on discovered objects."""
    db_path = get_db_path()
    engine = AssessmentEngine(db_path)
    print(f"[*] Running Modernization Assessment Engine on {db_path}...")
    summary = engine.assess_all(system_id="S21")
    results = summary.get("results", [])
    print(f"[+] Assessment complete: {len(results)} objects assessed (Run ID: {summary.get('run_id')}).")
    for r in results[:5]:
        print(f"  - {r.get('object_name')}: Target='{r.get('recommended_target')}', Score={r.get('overall_score')}/100, Risk={r.get('risk_level')}")
    if len(results) > 5:
        print(f"  ... and {len(results) - 5} more objects.")
    return 0

def cmd_generate(args):
    """Generates target artifacts for an approved migration plan."""
    db_path = get_db_path()
    gen = GenerationEngine(db_path)
    plan_id = args.plan_id
    space = args.space or "SALES_ANALYTICS"
    print(f"[*] Generating target artifacts for plan '{plan_id}' in space '{space}'...")
    try:
        res = gen.generate_for_plan(plan_id, space=space)
        print(f"[+] Successfully generated {res['total_artifacts']} artifacts in:")
        print(f"    {res['project_dir']}")
        return 0
    except Exception as e:
        print(f"[-] Generation failed: {e}", file=sys.stderr)
        return 1

def cmd_validate_package(args):
    """Validates sealed delivery package integrity, schemas, and credentials."""
    pkg_dir = args.package_dir
    validator = PackageValidator()
    print(f"[*] Validating delivery package at: {pkg_dir}")
    try:
        res = validator.validate_package(pkg_dir)
        print("=" * 60)
        print("PACKAGE VALIDATION RESULT")
        print("=" * 60)
        print(f"Status:            {'PASSED (VALID)' if res.is_valid else 'FAILED (INVALID)'}")
        print(f"Manifest Verified: {res.manifest_verified}")
        print(f"Files Checked:     {res.total_files_checked}")
        if res.corrupted_files:
            print(f"Corrupted Files ({len(res.corrupted_files)}):")
            for c in res.corrupted_files:
                print(f"  - {c}")
        if res.schema_errors:
            print(f"Schema Errors ({len(res.schema_errors)}):")
            for s in res.schema_errors:
                print(f"  - {s['file']}: {s['error']}")
        if res.security_findings:
            print(f"Security Findings ({len(res.security_findings)}):")
            for sec in res.security_findings:
                print(f"  - {sec}")
        print("=" * 60)
        return 0 if res.is_valid else 1
    except Exception as e:
        print(f"[-] Validation error: {e}", file=sys.stderr)
        return 1

def cmd_export_package(args):
    """Creates a sealed delivery package with manifest.json."""
    db_path = get_db_path()
    packager = DeliveryPackager(db_path)
    proj_id = args.project_id
    plan_id = args.plan_id
    version = args.version or "1.0.0"
    print(f"[*] Sealing delivery package for project '{proj_id}', plan '{plan_id}', version 'v{version}'...")
    try:
        pkg = packager.create_package(project_id=proj_id, plan_id=plan_id, version=version)
        print(f"[+] Package created successfully:")
        print(f"    Package ID:     {pkg['package_id']}")
        print(f"    Package Dir:    {pkg['package_dir']}")
        print(f"    Total Files:    {pkg['total_files']}")
        print(f"    Master SHA-256: {pkg['master_sha256']}")
        return 0
    except Exception as e:
        print(f"[-] Package sealing failed: {e}", file=sys.stderr)
        return 1

def cmd_runbook(args):
    """Generates execution runbook in Markdown and JSON."""
    db_path = get_db_path()
    gen = RunbookGenerator(db_path)
    proj_id = args.project_id or "proj-default"
    plan_id = args.plan_id
    space = args.space or "SALES_ANALYTICS"
    print(f"[*] Generating execution runbook for plan '{plan_id}'...")
    try:
        rb = gen.generate_runbook(project_id=proj_id, plan_id=plan_id, space=space)
        out_file = args.output or f"RUNBOOK_{plan_id}.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(rb["markdown_content"])
        print(f"[+] Runbook saved to: {out_file}")
        print(f"    Total Phases: {len(rb['phases'])}")
        return 0
    except Exception as e:
        print(f"[-] Runbook generation failed: {e}", file=sys.stderr)
        return 1

def cmd_restore_backup(args):
    """Restores database backup to a separate destination with verification."""
    db_path = get_db_path()
    mgr = DatabaseBackupManager(db_path)
    src = args.source
    dst = args.destination
    print(f"[*] Restoring backup from: {src}")
    print(f"[*] Target destination:    {dst}")
    try:
        report = mgr.restore_backup(src, dst, verify=args.verify)
        print("=" * 60)
        print("DATABASE RESTORE REPORT")
        print("=" * 60)
        print(f"Status:             {report['status']}")
        print(f"Integrity:          {'PASSED' if report['integrity_verified'] else 'FAILED'}")
        print(f"Tables Restored:    {report['table_count']}")
        print(f"Source SHA-256:     {report['source_sha256']}")
        print(f"Dest SHA-256:       {report['destination_sha256']}")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"[-] Restore failed: {e}", file=sys.stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(description="HANAMORPH BW Migration Studio CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", help="Display system and database status")

    # assess
    p_assess = subparsers.add_parser("assess", help="Run modernization assessment")

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate target artifacts for plan")
    p_gen.add_argument("--plan-id", required=True, help="Migration Plan ID")
    p_gen.add_argument("--space", default="SALES_ANALYTICS", help="Datasphere Space ID")

    # validate-package
    p_val = subparsers.add_parser("validate-package", help="Validate sealed delivery package")
    p_val.add_argument("--package-dir", required=True, help="Path to package directory")

    # export-package
    p_exp = subparsers.add_parser("export-package", help="Create sealed delivery package")
    p_exp.add_argument("--project-id", required=True, help="Project ID")
    p_exp.add_argument("--plan-id", required=True, help="Migration Plan ID")
    p_exp.add_argument("--version", default="1.0.0", help="Semantic version string")

    # runbook
    p_rb = subparsers.add_parser("runbook", help="Generate deployment runbook")
    p_rb.add_argument("--plan-id", required=True, help="Migration Plan ID")
    p_rb.add_argument("--project-id", default="proj-default", help="Project ID")
    p_rb.add_argument("--space", default="SALES_ANALYTICS", help="Target Datasphere space")
    p_rb.add_argument("--output", help="Optional output path for Markdown runbook")

    # restore-backup
    p_rst = subparsers.add_parser("restore-backup", help="Restore verified backup to a separate destination")
    p_rst.add_argument("--source", required=True, help="Source SQLite backup file")
    p_rst.add_argument("--destination", required=True, help="Target destination path (cannot be active DB)")
    p_rst.add_argument("--verify", action="store_true", default=True, help="Verify schema and integrity")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "status": cmd_status,
        "assess": cmd_assess,
        "generate": cmd_generate,
        "validate-package": cmd_validate_package,
        "export-package": cmd_export_package,
        "runbook": cmd_runbook,
        "restore-backup": cmd_restore_backup
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        return cmd_fn(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
