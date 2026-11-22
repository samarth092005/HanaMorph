# HANAMORPH BW Migration & Modernization Studio
# Existing Repository Code Mapping & Modernization Inventory — Architecture Blueprint 1.0

**Document Reference:** `BW-MIG-MAP-1.0`  
**Status:** Approved for Architecture Design  
**Target Studio:** `BW_Migration_Studio/bw-studio`  
**Classification:** SAP Enterprise Modernization Architecture  

---

## 1. Inventory Strategy & Classification Taxonomy

To ensure engineering continuity and prevent redundant rewrites, every existing module, class, endpoint, and table in `BW_Migration_Studio/bw-studio` is evaluated against the Architecture Blueprint 1.0 requirements.

### Classification Taxonomy:
- **`RETAIN`**: Production-ready, fully verified, meets all architectural requirements. Preserve as-is.
- **`IMPROVE`**: Strong foundation, but needs hardening, performance optimization, or edge-case handling.
- **`EXTEND`**: Functional for basic scenarios, but requires new capabilities (e.g., additional target engines, new object types).
- **`REPLACE WITH JUSTIFICATION`**: Flawed implementation that cannot meet architectural criteria; must be refactored with clear justification.
- **`NEW IMPLEMENTATION`**: Required architectural component currently missing from the codebase.
- **`BLOCKED BY PREREQUISITE`**: Cannot be implemented until external prerequisites (e.g., live RFC credentials, BTP service keys) are provisioned.

---

## 2. Comprehensive Source Code & Module Inventory

| Module Path / Component | Core Classes / Functions | Existing Status & Capabilities | Architectural Classification | Action & Architectural Alignment |
| :--- | :--- | :--- | :---: | :--- |
| **`server.py`** | `BWStudioHandler`, `do_GET`, `do_POST`, static file server, API dispatcher. | Serves HTTP port 4004; static jail and 403 traversal protection verified (DEF-04); passes tests. | **`IMPROVE`** | Retain static jail; modularize request routing into dedicated controller handlers; add async streaming for large discovery sweeps. |
| **`discovery.py`** | `DiscoveryEngine`, `ADTDiscoveryAdapter`, `CacheDiscoveryAdapter`, `discover_object`. | Extracts ADSO and HCPR structures; supports cached fixtures and basic ADT XML; handles TRCS (11 fields). | **`EXTEND`** | Decouple into two explicit pipelines: Level 1 (Lightweight Inventory) and Level 2 (Deep Discovery); add Query and DTP specialized extractors. |
| **`assessment.py`** | `AssessmentEngine`, `assess_object`, `generate_migration_plan`, `build_dependency_graph`. | Computes composite feasibility score and basic 4-tier risk; constructs DAG; passes all test cases. | **`IMPROVE`** | Decouple Feasibility ($S$) from Confidence ($C$); implement full 5-dimension scoring weights; add Tarjan's cycle breaker and topological wave clustering. |
| **`datasphere.py`** | `DatasphereGenerator`, `generate_csn`, `generate_hana_sql`, `generate_replication_flow`. | Object-semantic generation (ADSO $\rightarrow$ Local Table, HCPR $\rightarrow$ View); dynamic PK detection; `.flow.json` builder. | **`EXTEND`** | Retain existing CSN and DDL generators; add Analytic Model (`@Analytics.dataCategory: CUBE`) generation and Task Chain specifications. |
| **`bridge.py`** | *(Currently Missing)* | No dedicated BW Bridge artifact generator exists. | **`NEW IMPLEMENTATION`** | Build `BWBridgeGenerator` to output abapGit XML conversion packages for ADSOs, InfoObjects, and routine wrappers. |
| **`bdc.py`** | *(Currently Missing)* | No dedicated BDC Data Product generator exists. | **`NEW IMPLEMENTATION`** | Build `BDCGenerator` to output `data-product.json` manifests, BW Data Subscriptions, and Data Sharing Cockpit contracts. |
| **`hybrid.py`** | *(Currently Missing)* | No dedicated hybrid coexistence coordinator exists. | **`NEW IMPLEMENTATION`** | Build `HybridCoexistenceCoordinator` to generate dual-run CDC replication flows and cutover checklists. |
| **`validation.py`** | `ValidationEngine`, `validate_artifacts`, `validate_semantics`, `validate_dual_ddl`. | Real semantic validation; referential currency/unit integrity checks; dual DDL consistency (DEF-03). | **`EXTEND`** | Formalize into the 7-level validation framework; add Level 6 (CLI dry-run) and Level 7 (external reconciliation evidence ingestion). |
| **`packager.py`** | `DeliveryPackager`, `create_delivery_package`, dry-run scripts. | Bundles ZIP files with checksums; generates dry-run CLI scripts (`deploy_datasphere.sh`, `deploy_hana.sql`). | **`RETAIN`** | Maintain delivery packaging logic; add rollback shell script generator and runbook markdown builder. |
| **`db.py`** | SQLite helper functions, schema DDL, CRUD operations. | SQLite tables for systems, objects, assessments, waves, jobs, approvals; passes all tests. | **`IMPROVE`** | Enable SQLite WAL mode (`PRAGMA journal_mode = WAL;`); add Alembic migrations; prepare SQLAlchemy repository abstraction for BTP HANA Cloud. |
| **`connection_manager.py`** | `BWConnectionManager`, `DatasphereConnectionManager`, `BTPConnectionManager`. | Modular connection handlers; live socket check; credential isolation; read-only S21 checks. | **`IMPROVE`** | Retain strict read-only HTTP verb jail; add release auto-detection and least-privilege user verification. |
| **`connection_ui.py`** | Frontend connection modal and status manager. | Renders status indicators (`CONNECTED`, `NOT CONFIGURED`); handles connection testing. | **`RETAIN`** | Maintain responsive UI components; bind to new Level 1 Inventory trigger. |

---

## 3. API Endpoints Mapping & Classification

| HTTP Method | API Path | Handler Function | Current Status | Classification | Future Evolution |
| :---: | :--- | :--- | :---: | :---: | :--- |
| `GET` | `/api/v1/bw/connections` | `get_connections` | Verified | **`RETAIN`** | Return capability flags per connection. |
| `POST` | `/api/v1/bw/connections/test` | `test_connection` | Verified | **`IMPROVE`** | Enhance with release detection payload. |
| `GET` | `/api/v1/bw/inventory` | `get_inventory` | Missing / Partial | **`NEW IMPLEMENTATION`** | Expose Level 1 lightweight catalog list. |
| `POST` | `/api/v1/bw/discover` | `start_discovery` | Verified (Deep) | **`IMPROVE`** | Convert to async background job with status polling. |
| `GET` | `/api/v1/bw/assess` | `get_assessment` | Verified | **`IMPROVE`** | Include decoupled confidence and 5D breakdown. |
| `POST` | `/api/v1/bw/plan` | `generate_plan` | Verified | **`EXTEND`** | Support strategy allocation across all 4 routes. |
| `POST` | `/api/v1/bw/approve` | `record_approval` | Verified | **`EXTEND`** | Enforce 8-gate state machine with HMAC audit logs. |
| `POST` | `/api/v1/bw/generate` | `generate_targets` | Verified (DSP) | **`EXTEND`** | Support Bridge, BDC, and Hybrid generation dispatch. |
| `POST` | `/api/v1/bw/validate` | `run_validation` | Verified (Levels 1–3) | **`EXTEND`** | Support full 7-tier validation runner. |
| `GET` | `/api/v1/bw/package` | `download_package` | Verified | **`RETAIN`** | Stream signed ZIP delivery bundles. |

---

## 4. Test Suite Inventory & Baseline Preservation

The existing test suite (`tests/run_all_tests.py`) contains **43 automated test cases**, all currently passing (100% green).

### Test Coverage Preservation Invariant:
1. All 43 baseline unit and integration tests must continue to pass without regression during any architectural expansion.
2. New test suites will be introduced in parallel:
   - `test_inventory_l1.py` (Tests rapid catalog sweep and hashing).
   - `test_confidence_decoupling.py` (Tests $S_{total}$ vs. $C_{total}$ calculations).
   - `test_bridge_generation.py` (Tests abapGit XML structure).
   - `test_bdc_generation.py` (Tests BDC Data Product descriptors).
   - `test_validation_7tier.py` (Tests progressive Level 1–7 checks).
