# HANAMORPH BW MIGRATION STUDIO — PHASE 3–7 DEFECT REMEDIATION BASELINE

**Document Version:** 1.0.0  
**Date:** 2026-11-21  
**Project:** HANAMORPH — BW Migration & Modernization Studio  
**Audit Reference:** `docs/audits/PHASE_3_TO_7_INDEPENDENT_ACCEPTANCE_AUDIT.md`  
**Studio Path:** `BW_Migration_Studio/bw-studio`  
**Git Branch:** `feature/bw-migration-studio`  
**Baseline Test Status:** 29/29 Unit and Integration Tests Passing  

---

## 1. Executive Summary & Objective

An independent engineering audit of Phases 3–7 of the HANAMORPH BW Migration & Modernization Studio returned an **ACCEPTED WITH CONDITIONS** verdict. The audit verified strong end-to-end foundations (clean separation of concerns, zero-modification SAP invariants, 29 passing automated tests), but flagged six concrete defects that must be remediated before production delivery:

1. **DEF-04 (Critical Security):** Potential static file exposure and path traversal via `server.py` `SimpleHTTPRequestHandler` fallback.
2. **DEF-01 (Critical Generation):** One-size-fits-all generator logic generating physical column tables for analytical views (CompositeProviders, Queries, InfoSources) instead of true object-semantic definitions.
3. **DEF-03 (High Priority Validation):** Tautological Level 5 semantic validation that checked `True` without verifying currency/unit referential integrity or key definitions.
4. **DEF-05 (Medium Priority Parsing):** Static fallback field lists used in `cache_discovery_adapter.py` for BW Queries and InfoSources instead of parsing the actual XML elements.
5. **DEF-06 (Medium Priority Metadata):** Hardcoded primary key lists in ADT and Cache discovery adapters rather than parsing DDIC source keywords or ADSO `<keyElement>` tags.
6. **DEF-02 (High Priority Packaging):** Packaging discrepancies between generated artifacts and delivery manifests, plus missing honest dry-run deployment templates.

This document establishes the official engineering baseline, records reproduction evidence for all defects, and specifies the targeted, non-destructive remediation plan.

---

## 2. Baseline Test Execution Results

Prior to making any edits, the existing test suite was executed against the active repository state:

```
Ran 29 tests in 15.952s
OK
- test_assessment_engine: 3 tests OK
- test_connection_managers: 7 tests OK
- test_discovery_and_parsers: 2 tests OK
- test_end_to_end_engines: 6 tests OK
- test_generation_engine: 2 tests OK
- test_safety_guardrails: 4 tests OK
- test_server_live: 5 tests OK
```

All 29 tests pass against the pre-remediation code. All tests must continue to pass throughout remediation, augmented by new regression and defect-specific tests.

---

## 3. Defect Analysis & Reproduction Baseline

### DEF-04: Static File Exposure & Unrestricted Fallback (Critical Security)
- **Affected File:** `BW_Migration_Studio/bw-studio/backend/server.py` (lines 190–205).
- **Reproduction:** When an HTTP GET request is received that does not match any registered `/api/*` endpoint, `StudioRequestHandler.do_GET()` delegates to `super().do_GET()` (`http.server.SimpleHTTPRequestHandler`). Because `SimpleHTTPRequestHandler` operates relative to the current working directory, a path request like `/bw_studio.sqlite` or directory traversal sequences could potentially serve files outside the intended `frontend` directory.
- **Root Cause:** Absence of a canonical path jail restricted strictly to `FRONTEND_DIR`, and fallback to default `SimpleHTTPRequestHandler`.
- **Target Resolution:**
  1. Enforce strict static routing only within `FRONTEND_DIR`.
  2. Normalize and check canonical paths using `os.path.commonpath`.
  3. Explicitly reject any request targeting `.env`, `.sqlite`, `.master_key`, `.log`, `.git`, or parent directories (`..`).
  4. Return structured JSON 404 for unmapped API routes and static paths, eliminating `super().do_GET()` fallback.

### DEF-01: Object-Semantic Generators (Critical Generation)
- **Affected Files:**
  - `BW_Migration_Studio/bw-studio/generation_engine/generation_engine.py`
  - `BW_Migration_Studio/bw-studio/generation_engine/csn_generator.py`
  - `BW_Migration_Studio/bw-studio/generation_engine/hana_ddl_generator.py`
- **Reproduction:** When `generation_engine.generate_artifacts_for_object` is called for a CompositeProvider (`HCPR`), it calls `generate_entity_csn` (`kind: "entity"`) and `generate_column_table_ddl` (`CREATE COLUMN TABLE ...`). This produces physical table structures for analytical join/union views, violating SAP Datasphere semantic architecture.
- **Root Cause:** Single-path generation pipeline that treated all BW object types as physical tables.
- **Target Resolution:**
  1. Create distinct generation paths based on `object_type`:
     - `ADSO`: Local Table CSN (`kind: "entity"`, `@EndUserText.label`, keys) + HANA Column Table DDL (`COLUMN TABLE`).
     - `HCPR`: Analytic View CSN (`kind: "view"`, queries/unions) + HANA View DDL (`CREATE VIEW ... AS SELECT ...`).
     - `ELEM` (Query): Analytical Consumption Layer / Analytic Model CSN (`kind: "view"` or Analytic Model cube) or flagged `MANUAL_REDESIGN_REQUIRED`.
     - `TRCS` (InfoSource): Data pipeline / transformation mapping view or flagged `MANUAL_REDESIGN_REQUIRED`.
  2. Implement `generate_view_ddl` in `hana_ddl_generator.py`.
  3. Support generation statuses: `GENERATED`, `GENERATED_WITH_WARNINGS`, `PARTIAL`, `BLOCKED`, `UNSUPPORTED`.

### DEF-03: Real Semantic Validation (High Priority)
- **Affected File:** `BW_Migration_Studio/bw-studio/validation_engine/validation_engine.py`.
- **Reproduction:** Level 5 validation (`_validate_l5_semantic_integrity`) checked `if isinstance(csn_payload, dict): pass`, resulting in an automatic 100% pass rate even if currency/unit references were invalid or missing.
- **Root Cause:** Incomplete rule implementation where dictionary type assertion was used as a stub for semantic checks.
- **Target Resolution:**
  1. Check referential integrity: For any field of type `CURR` or with `@Semantics.amount.currencyCode`, verify that the referenced currency field exists within the entity elements.
  2. For any field of type `QUAN` or `@Semantics.quantity.unitOfMeasure`, verify that the referenced unit field exists.
  3. Verify primary key integrity (at least one key element for tables, or explicit reason if unkeyed).
  4. Verify view sources exist in the catalog or mapping.
  5. Support statuses: `PASS`, `WARNING`, `FAIL`, `BLOCKED`, `NOT_RUN`, `NOT_APPLICABLE`.

### DEF-05: Real Query and InfoSource XML Parsing (Medium Priority)
- **Affected File:** `BW_Migration_Studio/bw-studio/discovery/cache_discovery_adapter.py`.
- **Reproduction:** `parse_query_file` and `parse_trcs_file` returned static hardcoded field lists (`PURCHASE_REQ`, `DOC_TYPE`, etc.) rather than parsing the XML structure.
- **Root Cause:** Real XML structure was not fully traversed.
- **Target Resolution:**
  1. In `parse_trcs_file`: Parse the actual 11 fields present in `model.trcs` (`BANFN`, `BNFPO`, `BSART`, `MATNR`, `TXZ01`, `MENGE`, `MEINS`, `WERKS`, `LFDAT`, `AFNAM`, `EKGRP`) with real ABAP types and lengths.
  2. In `parse_query_file`: Extract `technicalName`, `description`, `providerName`, `infoArea` from `model.query`. Since formula/variable ASTs require live BEx runtime, extract structural metadata and mark field-level status as `PARTIAL` when query-specific formulas are not defined in the raw XML.

### DEF-06: Real Primary Key Detection (Medium Priority)
- **Affected Files:**
  - `BW_Migration_Studio/bw-studio/discovery/cache_discovery_adapter.py`
  - `BW_Migration_Studio/bw-studio/discovery/adt_discovery_adapter.py`
- **Reproduction:** `cache_discovery_adapter.py` determined primary keys via a hardcoded set: `f["name"] in ["ORDER_ID", "RECORD_ID", "ID"]`. Similarly, `adt_discovery_adapter.py` used a fallback name check.
- **Root Cause:** Simplified heuristic instead of parsing DDIC source keywords or ADSO `<keyElement>` tags.
- **Target Resolution:**
  1. In `cache_discovery_adapter.py`: Read `<keyElement>#///FIELDNAME</keyElement>` tags in `model.adso`. If missing or ambiguous, mark as `UNKNOWN`.
  2. In `adt_discovery_adapter.py`: Parse `<span class="keyword">key</span>` or key field markers in the DDIC table source HTML.

### DEF-02: Delivery Package Completeness & Honest Packaging (High Priority)
- **Affected File:** `BW_Migration_Studio/bw-studio/deployment/delivery_packager.py`.
- **Reproduction:** The packager created mock placeholder entries in the manifest that didn't match real disk outputs, and lacked deployment execution scripts.
- **Root Cause:** Packager was not wired to actual generated outputs from the GenerationEngine.
- **Target Resolution:**
  1. Package only files that exist on disk in `output/csn`, `output/ddl`, etc.
  2. Generate honest, safe dry-run deployment templates:
     - `deploy_datasphere.sh`: Validates CLI presence, runs `--dry-run` validation, explicitly warns about non-destructive execution.
     - `deploy_hana.sql`: Safe staging DDL with transaction handling comments.
  3. Ensure SHA-256 manifest includes every single packaged artifact.

### Additional Engineering Improvements
1. **Metadata Snapshot History:** Add non-destructive timestamped snapshot versioning to `DiscoveryEngine` and catalog persistence.
2. **Confidence Separation:** Decouple Assessment Confidence (measure of metadata completeness) from Feasibility Score (suitability for target architecture).
3. **4-Tier Risk Classification:** Standardize on `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` risk tiers with explicit criteria.

---

## 4. Remediation Safety Invariants

During all defect remediation steps, the following non-negotiable rules apply:
1. **SAP System S21:** Read-only invariant strictly preserved. Zero RFC/HTTP mutating requests, zero CTS transport requests.
2. **Local Workspaces:** No modification of the four existing HANAMORPH studios (`HanaMorph_DataSphere_Studio`, `HanaMorph_DWC_Studio`, `HanaMorph_Studio`, `HanaMorph_Web_Studio`).
3. **Version Control:** Branch `feature/bw-migration-studio` preserved; no `git push` or `git commit` actions.
4. **Target Environments:** Zero remote deployment calls to SAP Datasphere, BTP, or HANA Cloud. All outputs remain local specifications.

---

## 5. Execution Order

- **Step 1:** Complete baseline documentation (this document).
- **Step 2:** Remediate DEF-04 (Static file jail and traversal fix in `server.py`).
- **Step 3:** Remediate DEF-06 (Real primary key detection in ADT and Cache discovery adapters).
- **Step 4:** Remediate DEF-05 (Real Query and InfoSource XML parsing in `cache_discovery_adapter.py`).
- **Step 5:** Remediate DEF-01 (Object-semantic generators in `csn_generator.py`, `hana_ddl_generator.py`, `generation_engine.py`).
- **Step 6:** Remediate DEF-03 (Semantic validation engine refactoring in `validation_engine.py`).
- **Step 7:** Remediate DEF-02 (Delivery packager and honest deployment scripts in `delivery_packager.py`).
- **Step 8:** Implement snapshot history, decoupled confidence, and 4-tier risk classification.
- **Step 9:** Run full test suite with all new defect regression tests.
- **Step 10:** Compile final completion report `PHASE_3_TO_7_REMEDIATION_COMPLETION_REPORT.md`.
