# PRODUCTION READINESS GAP REGISTER & PRIORITIZED REMEDIATION ROADMAP

**Audit Date:** 2026-11-22  
**Scope:** BW Migration Studio (Milestones Post-M4.1 through M6)  
**Auditor Role:** Principal Enterprise Architect & Quality Lead  

---

## 1. Prioritized Gap Register

| Gap ID | Subsystem | Description & Impact | Severity | Priority | Recommended Remediation |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **GAP-01** | **M4.2 Transpiler** | **Identifier Collision in Lookups:** `_clean_identifier` strips `SOURCE_FIELDS-` resulting in `WHERE KOSTL = KOSTL;` (tautology) in SQLScript. | **High** | **P1 (Immediate)** | Prepend `:NEW.` or `SOURCE.` to right-hand lookup keys in `sql_translator.py`. |
| **GAP-02** | **M4.2 Transpiler** | **Multinary CONCATENATE:** Emits `CONCATENATE(a, b, c)` which is not a valid scalar function in SAP HANA SQL. | **Medium** | **P2 (Near-Term)** | Emit standard SQL concatenation operator `||` (`a || b || c`) in `sql_translator.py`. |
| **GAP-03** | **M4.2 Transpiler** | **String Quote Quadrupling:** String literals containing escaped quotes (`'O''Connor'`) are re-escaped into `'O''''Connor'`. | **Low** | **P3 (Maintenance)** | Unescape ABAP string tokens during parsing before re-escaping in SQL translator. |
| **GAP-04** | **M4.2 Generator** | **Decimal Dimension Misclassification:** In `sac_model_generator.py`, fields of type `DEC` default to Dimensions rather than Measures when explicit semantics are omitted. | **Medium** | **P2 (Near-Term)** | Default `DEC` fields to Measures with `SUM` aggregation unless marked as keys. |
| **GAP-05** | **M4.4 Frontend** | **Lack of Headless Browser E2E Tests:** Playwright is not installed in the environment; all frontend verifications are currently API-level. | **Medium** | **P2 (Near-Term)** | Request authorization to install `playwright==1.40.0` and run automated browser UI tests. |
| **GAP-06** | **M4.4 Security** | **API Key in LocalStorage:** Storing the backend API key in browser `localStorage` leaves it accessible to script injection. | **Medium** | **P2 (Near-Term)** | Migrate to HTTP-Only `SameSite=Strict` session cookies for browser clients. |
| **GAP-07** | **M5 Enterprise** | **Orphaned Running Jobs on Crash:** `BackgroundJobEngine` does not reconcile `RUNNING` jobs on server startup. | **Medium** | **P2 (Near-Term)** | Execute startup SQL sweep updating orphaned `RUNNING` jobs to `FAILED`. |
| **GAP-08** | **M5 Enterprise** | **Manual Database Restore:** Hot backup works via `PRAGMA` and `conn.backup()`, but no automated restore CLI command exists. | **Low** | **P3 (Maintenance)** | Implement `python cli.py restore-backup --backup-file <path>`. |
| **GAP-09** | **M6 Integration** | **Localhost-Only Adapter Binding:** Node.js adapter targets `http://127.0.0.1:4004`, lacking SAP BTP Destination Service or OAuth2 support. | **High** | **P1 (Pre-Cloud)** | Add SAP BTP Connectivity / Cloud Connector proxy support before cloud deployment. |

---

## 2. Answers to the Seven Essential Audit Questions

### 1. What is genuinely working?
- **Read-Only SAP Connectivity**: Safe, non-mutating discovery over ADT and RFC allowlists with zero DDIC modifications.
- **Canonical SQLite Storage**: Single canonical database (`bw_studio.sqlite`, 31 tables, WAL mode) with zero database file locking issues due to `SingleWriterQueue`.
- **Target Route Evaluation**: Multi-dimensional compatibility scoring across 4 primary modernization routes.
- **Delivery Packaging & Validation**: Automatic generation of `manifest.json`, cryptographic SHA-256 verification, and strict credential leak scanning.
- **CLI & Runbooks**: Full standalone CLI (`cli.py`) and 5-phase human/machine runbook generation.
- **135 Unit & Integration Tests**: 100% passing across 16 test modules.

### 2. What is implemented but not verified?
- **Actual Cloud Import/Deployment**: CSN 2.0 schemas, HANA SQL DDL, Replication Flow JSON, and SAC models are structurally valid but have not been deployed to live SAP Datasphere or SAC tenants.
- **Browser DOM E2E Interaction**: All 12 screen backend APIs pass 100%, but headless browser DOM rendering (Playwright) could not be executed due to missing test runner dependencies.

### 3. What is incomplete?
- **ABAP Transpiler Edge Cases**: Lookup where-clause parameter binding, multinary string concatenation syntax, and quote unescaping.
- **Background Job Restart Reconciliation**: Startup recovery sweep for crashed tasks.
- **Automated Restore Tooling**: CLI command for database restoration from verified backups.

### 4. What is unsafe?
- **Tautological Lookup WHERE Clause:** Generating `WHERE KOSTL = KOSTL;` in SQLScript lookups could cause full table scans or incorrect record joins if deployed without review.
- **LocalStorage Token Storage:** Frontend API key in `localStorage` should be transitioned to HTTP-Only cookies before multi-user deployment.
- *(Note: SAP S21 connectivity is 100% SAFE and strictly read-only).*

### 5. What prevents production readiness?
1. Remediation of GAP-01 (lookup parameter binding in ABAP transpiler).
2. Remediation of GAP-04 (`DEC` metric classification in SAC generator).
3. Installation of Playwright and automated execution of browser DOM test suite.

### 6. What is required before actual HANAMORPH integration?
1. Packaging `integration/bw_studio_adapter.js` into an npm package or placing it in the main platform's `src/services/` directory.
2. Integrating the adapter into the main HANAMORPH Express / CAP application lifecycle.
3. Defining mutual TLS or OAuth2 client credentials if deployed across separate hosts or cloud containers.

### 7. What should be the next engineering milestone?
**Milestone M6.1 — Transpiler Polish & Main Platform Live Integration**:
1. Fix GAP-01, GAP-02, GAP-03, and GAP-04.
2. Add startup orphaned job reconciliation (GAP-07).
3. Import `BWStudioAdapter` into the main HANAMORPH application and verify live cross-process communication.
