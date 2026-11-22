# HANAMORPH BW MIGRATION STUDIO
# MILESTONE M4.1 — REMAINING GAPS & DEFERRED ROADMAP REGISTER

**Report Date:** 2026-11-22  
**Evaluation Target:** Post-M4.1 Standalone Application Baseline  
**Scope Directive:** M4.1 is strictly hardened; all deferred features tracked for M4.2–M4.4  

---

## 1. M4.1 Remediation Scorecard

The following table tracks the resolution of gaps identified during the Baseline Audit:

| Gap ID | Description | Severity | M4.1 Status | Resolution Summary |
| :---: | :--- | :---: | :---: | :--- |
| **GAP-01** | Dual SQLite Database Divergence | **HIGH** | **REMEDIATED** | Unified on `database/bw_studio.sqlite`. Backed up both, merged synthetic test data non-destructively, redirected `verify_synthetic_e2e.py`. Legacy file preserved intact. |
| **GAP-02** | Unauthenticated REST API | **HIGH** | **REMEDIATED** | Enforced Bearer & X-API-Key token authentication with constant-time HMAC comparison on all `/api/*` endpoints. Public health checks preserved. |
| **GAP-03** | Single-Threaded HTTP Server Bottleneck | **HIGH** | **REMEDIATED** | Upgraded `server.py` to `ThreadedHTTPServer` (`socketserver.ThreadingMixIn`). Non-blocking I/O verified under concurrent traffic. |
| **GAP-04** | Missing Python Dependency Manifests | **MEDIUM** | **REMEDIATED** | Authored `requirements.txt` and `pyproject.toml` documenting required (`cryptography`) and optional (`pyrfc`) dependencies. |

---

## 2. Deferred Technical Gaps & Future Roadmap

The following technical enhancements remain intentionally deferred to subsequent milestones according to the architecture roadmap:

### Deferred to Milestone M4.2: Transformation & Modernization Intelligence

#### GAP-05: Advanced ABAP Routine Modernization Depth
- **Current State:** Start routines, end routines, and field routines are identified and scored with high complexity/risk penalties. Preliminary code templates exist in `transformation_engine.py`, but automated AST-level transpilation into HANA SQLScript or Datasphere calculated columns is skeletal.
- **Risk:** Complex ABAP transformations require manual developer translation during migration.
- **Target Milestone:** M4.2 (Transformation Engine Hardening).
- **Remediation Plan:** Implement an AST-based ABAP-to-SQL rule transpiler for common patterns (`SELECT SINGLE`, `CONCATENATE`, lookup joins, and mathematical expressions).

#### GAP-07: Datasphere CSN / Replication Flow Generator Expansion
- **Current State:** Generates standalone table CSN definitions (`kind: entity`) and HANA column table SQL DDL.
- **Gap:** Does not yet generate native SAP Datasphere Replication Flow JSON specifications or Analytical Dataset metadata for SAP Analytics Cloud consumption.
- **Target Milestone:** M4.2 (Generation Engine Expansion).
- **Remediation Plan:** Expand `generation_engine/generator.py` with templates for Datasphere Replication Flows and SAC-ready Analytical Model views.

---

### Deferred to Milestone M4.3: Enterprise Packaging & Delivery Integration

#### GAP-08: Datasphere CLI Integration & Direct Importer Hook
- **Current State:** Generates self-contained sealed ZIP delivery packages containing CSN, DDL, mapping documents, and SHA-256 manifests.
- **Gap:** Deploying artifacts into Datasphere currently requires manual import via the Datasphere Web UI or manual invocation of the `@sap/datasphere-cli`.
- **Target Milestone:** M4.3 (Delivery & Deployment Automation).
- **Remediation Plan:** Introduce an optional, operator-approved deployment hook executing `datasphere spaces modeling import` via local CLI wrappers.

#### GAP-09: Automated Migration Runbook & Rollback Generator
- **Current State:** Lineage diagrams and wave execution sequences are exported in package metadata.
- **Gap:** Lacks an automated runbook generator creating step-by-step PDF/Markdown operational execution guides with rollback checklists.
- **Target Milestone:** M4.3.
- **Remediation Plan:** Add a runbook generator in `deployment/delivery_packager.py`.

---

### Deferred to Milestone M4.4: Frontend Modularization & Visual Enhancements

#### GAP-06: Monolithic Frontend Single-File Architecture
- **Current State:** `frontend/index.html` is a single file of ~2,130 lines containing CSS, HTML, and JavaScript.
- **Assessment:** Fully functional, responsive, and decoupled from external CDNs, but large for long-term collaborative maintenance.
- **Target Milestone:** M4.4 (Frontend Architecture Refactoring).
- **Remediation Plan:** Split `index.html` into modular components (`static/css/`, `static/js/api.js`, `static/js/graph.js`, `static/js/screens/`).

#### GAP-10: Automated Browser UI End-to-End Test Suite
- **Current State:** Backend REST API is verified with 92 passing unit/integration tests and synthetic E2E pipeline. Frontend UI interactions are currently verified manually or via HTTP responses.
- **Target Milestone:** M4.4.
- **Remediation Plan:** Add Playwright/Puppeteer automated browser UI test scripts for all 12 screens.

---

## 3. Risk Assessment & Blockers

- **Blockers:** **NONE.** All M4.1 requirements are satisfied and verified.
- **SAP S21 Safety:** **100% SECURE.** Zero-mutation directives enforced and verified.
- **Persistence Integrity:** **100% UNIFIED.** Canonical database backed up and verified.
- **Production Foundation Status:** **APPROVED TO PROCEED TO M4.2.**
