# HANAMORPH — Milestone M1 Remaining Risks and Pre-M2 Action Plan
## Enterprise Risk Register and Mitigation Roadmap

---

### DOCUMENT CONTROL
- **Document ID**: `HANAMORPH-AUDIT-M1-RISKS`
- **Audit Target**: Remaining Risks Post-Milestone M1 & Pre-M2 Prerequisites
- **Target Repository**: `BW_Migration_Studio/bw-studio`
- **Branch**: `feature/bw-migration-studio`
- **Auditor Role**: Independent Enterprise Risk & Reliability Auditor
- **Audit Date**: November 2026
- **Status**: Active Risk Register

---

## 1. RISK ASSESSMENT MATRIX

The independent audit evaluated remaining architectural, operational, and software reliability risks following the completion of Milestone M1. Each risk is evaluated across **Likelihood**, **Impact**, and **Detection Difficulty**:

```
IMPACT
  ▲
  │   [R-02: Lock Contention]     [R-01: Queue Crash]
H │
  │   [R-04: PyRFC Dependency]    [R-05: Graph Memory]
M │
  │   [R-03: Package Drift]
L │
  └────────────────────────────────────────────────►
      L                          M                  H
                         LIKELIHOOD
```

| Risk ID | Risk Category | Description | Likelihood | Impact | Overall Severity | Pre-M2 Gate |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **R-01** | Database Reliability | `SingleWriterQueue` worker thread crashes on unhandled batch exceptions, locking DB file and stalling queue. | Medium | High | **HIGH** | **MANDATORY GATE** |
| **R-02** | Concurrency & Data | Legacy engines write directly to SQLite, causing `SQLITE_BUSY` errors during M2 parallel discovery. | High | Medium | **MEDIUM** | **MANDATORY GATE** |
| **R-03** | Metadata Fidelity | `CanonicalObject.content_fingerprint` omits `package`, failing to detect $TMP to transport package drift. | Low | Low | **LOW** | **SPRINT M2 DAY 1** |
| **R-04** | Deployment | Native SAP NW RFC SDK C-library dependency (`pyrfc`) fails to load in headless container environments. | Medium | Medium | **MEDIUM** | **MONITORED (MOCK OK)**|
| **R-05** | Scalability | In-memory Tarjan SCC graph analysis consumes excessive RAM on massive SAP landscapes (>50,000 objects). | Low | Medium | **MEDIUM** | **MILESTONE M3** |

---

## 2. DETAILED RISK PROFILES & REMEDIATION PLANS

### Risk R-01: SingleWriterQueue Thread Death on Unhandled Batch Item Error
- **Risk Severity**: **HIGH**
- **Root Cause**:
  In `database/sqlite_queue.py`, `_writer_loop()` invokes `_write_batch_with_retry()`. If a batch contains an item with unexpected structure or types (e.g. missing `'stable_urn'`), an exception is raised that is not caught inside the loop. The thread terminates silently without executing `conn.close()`.
- **Operational Impact**:
  1. Under Windows, the unclosed SQLite connection causes `WinError 32: The process cannot access the file because it is being used by another process`.
  2. `self._is_running` remains `True`. Subsequent calls to `enqueue()` succeed in putting items in memory, but no thread consumes them, causing the entire ingestion pipeline to freeze.
- **Mandatory Pre-M2 Remediation**:
  1. Add top-level `try...finally` in `_writer_loop` ensuring `conn.close()` is executed and `self._is_running = False` is set on thread exit.
  2. Implement item-level exception catching within batch processing.
  3. Introduce a **Dead-Letter Queue (DLQ)** list where corrupted items are stored with error diagnostics, allowing valid batch items to proceed and commit.

---

### Risk R-02: Legacy Engine Direct SQLite Write Lock Contention
- **Risk Severity**: **MEDIUM**
- **Root Cause**:
  Engines implemented prior to M1 (`discovery_engine.py`, `assessment_engine.py`, `planning_engine.py`, `generation_engine.py`, `validation_engine.py`, `delivery_packager.py`) establish ad-hoc `sqlite3.connect()` instances with direct `INSERT` and `UPDATE` statements.
- **Operational Impact**:
  SQLite WAL mode permits multiple concurrent readers, but **only a single writer connection** can hold the write lock. When Milestone M2 launches concurrent background discovery extractors (pulling DataSources, InfoObjects, and ADSOs in parallel threads), direct writes will collide with the `SingleWriterQueue`, triggering `sqlite3.OperationalError: database is locked`.
- **Mandatory Pre-M2 Remediation**:
  Centralize all engine write paths through the `SingleWriterQueue` instance managed by `DatabaseManager`. Convert engine write methods to enqueue write commands or use a unified DAO interface.

---

### Risk R-03: Content Fingerprint Omitting Package Drift
- **Risk Severity**: **LOW**
- **Root Cause**:
  `CanonicalObject.content_fingerprint` serializes all core attributes into a JSON payload for SHA-256 hashing, but omits `self.package`.
- **Operational Impact**:
  If a BW asset is moved from a local test package (`$TMP`) to a production transport package (`Z_BW_CORE`), the calculated fingerprint will not change. In Milestone M2 incremental delta discovery, the change would not be detected as a modification.
- **Pre-M2 Remediation**:
  Add `"package": self.package` into the `canonical_payload` dictionary in `CanonicalObject.content_fingerprint`.

---

### Risk R-04: PyRFC Native Library Dependency in Container Environments
- **Risk Severity**: **MEDIUM**
- **Root Cause**:
  `pyrfc` requires the SAP NetWeaver RFC SDK C/C++ shared libraries (`libsapnwrfc.so` on Linux, `sapnwrfc.dll` on Windows), which cannot be distributed publicly via PyPI and require proprietary SAP customer credentials to download.
- **Operational Impact**:
  Automated CI/CD pipelines and client container deployments lacking the NW RFC SDK binaries will fail to initialize RFC connectors.
- **Mitigation Strategy**:
  1. The M1 implementation already provides `MockRFCClient` as an automated fallback when `pyrfc` is absent.
  2. In production deployment documentation, clearly document the optional status of PyRFC (HTTP/REST via ADT/OData is the primary interface; RFC is strictly for benign diagnostics).
  3. Ensure application startup succeeds gracefully in mock RFC mode when SDK libraries are missing.

---

### Risk R-05: In-Memory Dependency Graph Memory Footprint on Large SAP Estates
- **Risk Severity**: **MEDIUM**
- **Root Cause**:
  The M1 `DependencyGraph` loads nodes and adjacency lists into memory for Tarjan's SCC cycle analysis. On enterprise SAP BW estates with 50,000+ objects and 200,000+ lineage edges, in-memory graph representation may consume significant memory (~200MB - 500MB).
- **Operational Impact**:
  Potential memory pressure in resource-constrained container environments (e.g., standard SAP BTP Cloud Foundry 1GB memory limit).
- **Mitigation Strategy (Scheduled for Milestone M3)**:
  1. In Milestone M3, implement streaming chunked graph generation.
  2. Implement database-backed edge traversal using SQLite recursive CTEs (`WITH RECURSIVE`) to offload subgraph traversal to the indexed database.

---

## 3. PRE-M2 AUTHORIZATION ACTION CHECKLIST

Before engineering work on Milestone M2 begins, the following checklist must be completed and verified:

```markdown
- [ ] Task 1: Refactor `_writer_loop` in `database/sqlite_queue.py` with `try...finally` connection cleanup.
- [ ] Task 2: Implement Dead-Letter Queue (DLQ) in `database/sqlite_queue.py` for malformed batch items.
- [ ] Task 3: Add `"package": self.package` to `CanonicalObject.content_fingerprint` in `models/canonical_model.py`.
- [ ] Task 4: Refactor `discovery_engine.py` to route database writes through `SingleWriterQueue`.
- [ ] Task 5: Execute test suite to confirm all 66 tests pass with 0 regressions.
```

Once Tasks 1–5 are completed, Milestone M2 is authorized for full development.
