# HANAMORPH BW Migration & Modernization Studio
# Architecture Decision Register (ADR) — Architecture Blueprint 1.0

**Document Reference:** `BW-MIG-ADR-1.0`  
**Status:** Approved Architecture Decisions  
**Target Studio:** `BW_Migration_Studio/bw-studio`  
**Classification:** SAP Enterprise Modernization Architecture  

---

## 1. Index of Architecture Decision Records (ADRs)

- **ADR-001:** Strict Separation of Metadata Modernization and Bulk Data Movement
- **ADR-002:** Canonical Metadata Model as Intermediate Representation (IR)
- **ADR-003:** Two-Level Discovery Pipeline (Lightweight Inventory vs. Selective Deep Discovery)
- **ADR-004:** Decoupled Confidence Scoring vs. Technical Feasibility Scoring
- **ADR-005:** Four Autonomous Target Generation Strategies (Datasphere, Bridge, BDC, Hybrid)
- **ADR-006:** Formal 8-Gate Human-in-the-Loop (HITL) Governance State Machine
- **ADR-007:** 7-Level Validation Framework with Out-of-Process Reconciliation Evidence
- **ADR-008:** Progressive Storage Architecture (SQLite WAL Local to SAP HANA Cloud on BTP)
- **ADR-009:** Strict Defense-in-Depth Read-Only Protection for SAP S21 Benchmark System
- **ADR-010:** Standardized Native CSN 2.0 and SQL DDL Generation over Proprietary Formats

---

## 2. Detailed Architecture Decision Records

### ADR-001: Strict Separation of Metadata Modernization and Bulk Data Movement
- **Status:** **ACCEPTED**
- **Context:** SAP BW landscapes contain multi-terabyte transactional tables. A naive migration tool might attempt to extract business records into local Python memory for transformation.
- **Decision:** HANAMORPH operates exclusively as a **Metadata and Logic Modernization Engine**. It never extracts, buffers, or transforms bulk business records. All bulk data movement is delegated to SAP-native replication mechanisms (Replication Flows, DP Agent, SLT).
- **Consequences:** Eliminates memory exhaustion risks, prevents GDPR/PII violations, and adheres to enterprise data governance standards.

---

### ADR-002: Canonical Metadata Model as Intermediate Representation (IR)
- **Status:** **ACCEPTED**
- **Context:** Connecting heterogeneous BW source versions directly to multiple cloud targets results in an $M \times N$ complexity explosion.
- **Decision:** Introduce a normalized, technology-neutral Canonical Metadata Model using deterministic URNs (`urn:sap:bw:<system>:<type>:<name>`). Source extractors map to this Intermediate Representation; target engines generate artifacts from it.
- **Consequences:** Reduces complexity to $M + N$. Adding a new source release or cloud target requires only a single new adapter.

---

### ADR-003: Two-Level Discovery Pipeline
- **Status:** **ACCEPTED**
- **Context:** Recursive deep discovery across 50,000+ BW objects triggers network saturation, dialog timeouts, and unmanageable memory footprints.
- **Decision:** Split discovery into:
  1. *Level 1 Lightweight Inventory:* Rapid catalog sweep capturing scalar attributes (type, name, infoarea, active status, change date) in $< 15$ seconds.
  2. *Level 2 Selective Deep Discovery:* In-depth syntactic and semantic extraction constrained strictly to user-scoped InfoAreas.
- **Consequences:** Eliminates production BW server strain while giving architects immediate landscape visibility.

---

### ADR-004: Decoupled Confidence Scoring vs. Technical Feasibility Scoring
- **Status:** **ACCEPTED**
- **Context:** An object might have simple 1:1 mapping rules (high feasibility), but its underlying transformation routine code was missing or truncated during extraction. Coupling these scores produces dangerous false positives.
- **Decision:** Decouple Feasibility ($S_{total} \in [0, 100]$) from Confidence ($C_{total} \in [0.0, 1.0]$).
  - $S_{total}$: Measures technical compatibility with the target platform.
  - $C_{total}$: Measures completeness and depth of the extracted metadata evidence.
- **Consequences:** Architects are alerted when a "high feasibility" score is backed by low-confidence evidence, preventing premature migration approval.

---

### ADR-005: Four Autonomous Target Generation Strategies
- **Status:** **ACCEPTED**
- **Context:** Enterprise BW workloads cannot all move to Native Datasphere (due to legacy ABAP routines) nor should they all be locked in BW Bridge (due to licensing costs).
- **Decision:** Support four distinct, production-grade modernization routes:
  1. *Native SAP Datasphere:* CSN 2.0 Local Tables, Views, Analytic Models, Replication Flows.
  2. *SAP BW Bridge:* abapGit XML packages and BTP ABAP Cloud routine wrappers.
  3. *SAP Business Data Cloud (BDC):* BW Data Subscriptions and Data Sharing Cockpit products.
  4. *Hybrid Modernization:* Coexistence, dual-run replication, and phased cutover.
- **Consequences:** Provides maximum flexibility for enterprise modernization programs.

---

### ADR-006: Formal 8-Gate Human-in-the-Loop (HITL) Governance State Machine
- **Status:** **ACCEPTED**
- **Context:** Automated batch generation without human checkpoints risks deploying flawed models to cloud data warehouses.
- **Decision:** Enforce an 8-gate approval state machine. Every major boundary (Scope, Strategy, Redesign, Waves, Generation, Replication, Validation, Cutover) requires explicit digital sign-off and records an immutable HMAC-signed audit entry.
- **Consequences:** Guarantees enterprise audit compliance and accountability across the entire migration lifecycle.

---

### ADR-007: 7-Level Validation Framework with Out-of-Process Reconciliation Evidence
- **Status:** **ACCEPTED**
- **Context:** Verifying generated models requires more than simple syntax checks, but data reconciliation must not ingest bulk records into the studio.
- **Decision:** Implement a 7-level validation framework:
  - Levels 1–5: In-engine syntactic, semantic, referential, and graph checks.
  - Level 6: External CLI dry-run validation against target space metadata.
  - Level 7: Ingestion of out-of-process reconciliation evidence (source vs. target record counts, aggregate measure sums, checksum hashes).
- **Consequences:** Complete semantic and business data parity proof without violating the metadata-only processing invariant.

---

### ADR-008: Progressive Storage Architecture
- **Status:** **ACCEPTED**
- **Context:** The studio must run smoothly on a local developer workstation while scaling to multi-tenant enterprise deployment on SAP BTP Cloud Foundry.
- **Decision:**
  - *Local Mode:* SQLite 3 with Write-Ahead Logging (WAL) enabled (`PRAGMA journal_mode = WAL;`).
  - *Cloud Mode:* SAP HANA Cloud / PostgreSQL on SAP BTP accessed via SQLAlchemy repository abstraction.
- **Consequences:** Zero external dependencies for local testing, seamless migration to enterprise cloud infrastructure.

---

### ADR-009: Strict Defense-in-Depth Read-Only Protection for SAP S21
- **Status:** **ACCEPTED**
- **Context:** The SAP test user `int_samarth` possesses unrestricted `SAP_ALL` authorizations on SAP reference system `S21`.
- **Decision:** Hardcode an unbypassable HTTP verb jail (allowing only `GET` and `HEAD`), restrict RFC calls to an explicit read-only whitelist, block CTS transport generation, and mandate a least-privilege `Z_BW_MIGRATION_READ` role.
- **Consequences:** Eliminates any possibility of accidental repository modification or data corruption on SAP S21.

---

### ADR-010: Standardized Native CSN 2.0 and SQL DDL Generation over Proprietary Formats
- **Status:** **ACCEPTED**
- **Context:** Emitting proprietary or undocumented configuration formats creates vendor lock-in and breaks upon SAP platform upgrades.
- **Decision:** Standardize all Datasphere target artifacts on official SAP Core Data Services CSN 2.0 schemas (`type: "entity"`, `type: "view"`, `@Analytics.dataCategory: "CUBE"`) and SAP HANA Cloud Column Table SQL DDL.
- **Consequences:** Ensures full forward compatibility with official SAP Datasphere CLI tooling and native BTP deployments.
