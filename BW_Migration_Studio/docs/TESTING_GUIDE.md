# HANAMORPH — Automated Testing and QA Guide

## 1. TEST ARCHITECTURE OVERVIEW
The HANAMORPH test suite is architected to provide 100% test coverage across all critical backend engines, security guardrails, concurrency mechanisms, and data pipelines without requiring active live connections to external SAP systems.

- **Test Runner**: `tests/run_all_tests.py` using Python's standard `unittest` framework.
- **Total Test Cases**: 69 automated tests.
- **Execution Time**: ~35 seconds.
- **Pass Rate**: 100% (69/69 passing, 0 failures, 0 errors).

---

## 2. TEST SUITES INVENTORY

### 2.1 Concurrency & Database Suite (`TestSingleWriterQueue`, `TestDatabaseInit`)
- Verifies WAL mode pragmas and busy timeout configuration.
- Tests multi-threaded concurrent write throughput.
- Tests dead-letter queue (DLQ) item isolation upon malformed SQL.
- Tests backpressure handling and queue capacity limits.
- Tests graceful shutdown and resource cleanup via `try...finally`.

### 2.2 Security & Connector Suite (`TestBWConnectionManager`, `TestADTDiscovery`)
- Tests HTTP verb jail: asserts `POST`, `PUT`, `DELETE` to SAP S21 throw `SAPSecurityViolationError`.
- Tests RFC whitelist: asserts non-whitelisted function modules are rejected.
- Tests credential masking in logging outputs and diagnostic API responses.

### 2.3 Discovery Suite (`TestDiscoveryEngine`, `TestCanonicalModel`)
- Tests extraction of ADSOs, InfoObjects, Transformations, and Process Chains.
- Tests offline bundle ingestion (`import_metadata_bundle`) and provenance assignment (`IMPORTED`).
- Tests deterministic SHA-256 content fingerprinting including ABAP package validation (Condition C-03).
- Tests snapshot registration in `discovery_snapshots`.

### 2.4 Assessment & Scoring Suite (`TestAssessmentEngine`)
- Tests 5-dimension weighted scoring calculation.
- Tests 4-route classification logic (`native_datasphere`, `bw_bridge`, `bdc_data_product`, `hybrid`).
- Tests complexity tier grouping (Low, Medium, Complex, Highly Complex).

### 2.5 Planning & DAG Sequencing Suite (`TestPlanningEngine`)
- Tests topological sort on dependency graphs.
- Tests cycle detection and soft cycle decoupling.
- Tests project creation and human approval gate transitions (`DRAFT` -> `APPROVED`).

### 2.6 Generation Suite (`TestGenerationEngine`)
- Tests rejection of unapproved architecture plans.
- Tests CSN schema generation compliance against SAP CAP specification.
- Tests SAP HANA Cloud SQL DDL generation.
- Tests artifact registration and SHA-256 hash persistence in `generated_artifacts`.

### 2.7 Validation & Delivery Suite (`TestValidationEngine`, `TestDeliveryPackager`)
- Tests all 7 validation levels (119 checks).
- Tests severity tiering (`ERROR`, `WARNING`, `INFO`).
- Tests delivery gate blocking when errors exist.
- Tests ZIP packaging, `manifest.json` generation, and SHA-256 checksum sealing in `delivery_packages`.

---

## 3. HOW TO EXECUTE TESTS

### 3.1 Run Complete Test Suite
```powershell
cd C:\Users\samarth\BW-hanamorph\BW_Migration_Studio\bw-studio
python tests\run_all_tests.py
```

### 3.2 Run Specific Engine Tests
```powershell
python -m unittest tests.test_sqlite_queue
python -m unittest tests.test_validation_engine
python -m unittest tests.test_generation_engine
```
