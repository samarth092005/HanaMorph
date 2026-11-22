# HANAMORPH BW Migration & Modernization Studio
# Milestone M1 Engineering Implementation Plan

**Document Reference:** `BW-MIG-PLAN-M1`  
**Status:** Approved for Implementation  
**Target Studio:** `BW_Migration_Studio/bw-studio`  
**Classification:** SAP Enterprise Modernization Engineering Plan  
**Date:** November 21, 2026  

---

## 1. Executive Summary & Objective

Milestone M1 establishes the core engineering foundations of HANAMORPH BW Migration Studio in strict adherence to the conditionally approved architecture:
1. **Canonical Metadata Identity & Model:** Deterministic URNs (`urn:sap:bw:<system>:<client>:<type>:<escaped_name>:<version>`), SHA-256 canonical fingerprints, and lossless DDIC typing.
2. **Database Hardening & Single-Writer Ingestion Queue:** SQLite WAL configuration, bounded producer-consumer queue, transaction rollback, retry rules, and checkpointing.
3. **Connection Security & Benign RFCs:** Read-only HTTP verb jail (GET/HEAD only), benign RFC diagnostics (`RFC_PING`, `STFC_CONNECTION`), credential masking, and zero user-detail BAPIs.
4. **Dependency Graph & Cycle Analysis Foundations:** Tarjan SCC detection, hard vs. soft dependency edge classification, edge preservation, and manual redesign flagging.
5. **Comprehensive Verification:** 100% preservation of the 43 baseline tests plus exhaustive new test suites covering all M1 criteria.

---

## 2. Pre-Implementation Baseline

- **Repository Branch:** `feature/bw-migration-studio` (preserved; zero resets or stashes).
- **Existing User Modifications:** Preserved across `.gitignore`, `backend/server.py`, `frontend/index.html`, and `tests/`.
- **Baseline Test Results:** 43 tests passing in 30.292s (`Ran 43 tests, OK`).
- **Target Directories:**
  - Code: `BW_Migration_Studio/bw-studio/`
  - Docs: `BW_Migration_Studio/docs/architecture/` (mirrored in `docs/architecture/`)

---

## 3. Sub-Stage Breakdown & Detailed Tasks

### Stage M1.1 — Baseline and Implementation Plan (Completed)
- Document current system baseline, file inventory, and test benchmarks.
- Author `M1_IMPLEMENTATION_PLAN.md`.

### Stage M1.2 — Canonical Identity and Metadata Model
- Create `BW_Migration_Studio/bw-studio/models/canonical_model.py`:
  - `CanonicalURN`: Normalization, URL escaping for `/NAMESPACE/NAME`, system/client extraction, validation, and string formatting.
  - `CanonicalObject`: Attributes for URN, system, client, type, technical name, version (`A`/`M`/`D`), description, InfoArea, active status, extracted timestamp, content fingerprint, provenance, completeness, and confidence.
  - Deterministic serialization (sorted keys, ISO timestamps) and SHA-256 fingerprint generation.
  - Detection of content mutations even when extraction timestamps remain unchanged.

### Stage M1.3 & M1.4 — Database Migrations, SQLite Hardening & Single-Writer Ingestion Queue
- Enhance `BW_Migration_Studio/bw-studio/database/schema_manager.py`:
  - Add Migration 6: Table `canonical_bw_objects`, `canonical_object_fields`, `canonical_dependencies`, and `canonical_snapshots` supporting URNs, content fingerprints, provenance, and versions.
  - Maintain compatibility with both fresh test databases and existing databases.
- Create `BW_Migration_Studio/bw-studio/database/sqlite_queue.py`:
  - `SingleWriterQueue`: Bounded in-memory queue (`queue.Queue`) with configurable maxsize (default: 5,000) enforcing backpressure.
  - Dedicated background writer thread executing batch upserts in single atomic transactions.
  - Graceful shutdown (`shutdown(timeout=10)`), flushing remaining records.
  - Transaction rollback on batch errors with retry policies.
  - Explicit WAL configuration (`PRAGMA journal_mode = WAL;`, `PRAGMA busy_timeout = 10000;`, `PRAGMA synchronous = NORMAL;`).
  - WAL checkpointing (`PRAGMA wal_checkpoint(TRUNCATE);`) and database integrity checking (`PRAGMA integrity_check;`).

### Stage M1.5 — Connection Manager Security Boundaries
- Harden `BW_Migration_Studio/bw-studio/connectors/bw_connection_manager.py`:
  - Strict HTTP verb jail: Permits `GET` and `HEAD` only; immediately raises `SecurityViolationError` on `POST`, `PUT`, `DELETE`, `PATCH`.
  - Block activation, locking, CTS transport endpoints.
  - Benign RFC diagnostics: Supports `RFC_PING` and `STFC_CONNECTION` only.
  - Eliminate any dependency on `BAPI_USER_GET_DETAIL` or `RFC_READ_TABLE`.
  - Absolute credential masking in all error messages, details, and logs (`[REDACTED]`).
- Create `BW_Migration_Studio/bw-studio/connectors/mock_rfc.py`:
  - Mocked RFC testing harness allowing 100% offline verification of benign RFC execution without live SAP hardware.

### Stage M1.6 — Dependency Graph and Cycle Analysis Foundations
- Enhance `BW_Migration_Studio/bw-studio/dependency_engine/dependency_graph.py`:
  - Implement **Tarjan's Strongly Connected Components (SCC)** algorithm to identify all cyclical subgraphs.
  - Edge classification: `PRIMARY_DATA_FLOW` (hard ETL) vs. `LOOKUP_DEPENDENCY` (soft routine lookup) vs. `SEMANTIC_LINK`.
  - Edge preservation invariant: Zero automatic edge deletion.
  - Deterministic cycle analysis: Classify Type 1 (Self-loop), Type 2 (Lookup-induced), and Type 3 (Mutual interlocking).
  - Explicit cycle flags and manual redesign recommendation generator.

### Stage M1.7 — Regression Tests, Integration Tests & Documentation
- Build comprehensive test suites in `BW_Migration_Studio/bw-studio/tests/`:
  - `test_m1_canonical_model.py`: URN parsing, namespace escaping, version tracking, fingerprint generation.
  - `test_m1_database_and_queue.py`: WAL mode, single-writer queue concurrency, backpressure, rollback, integrity checks.
  - `test_m1_connectivity_security.py`: HTTP verb whitelist, forbidden endpoint blocks, benign RFC mocks, credential sanitization.
  - `test_m1_dependency_cycle.py`: Tarjan SCC detection, edge classification, edge preservation, manual redesign flags.
- Register new tests in `BW_Migration_Studio/bw-studio/tests/run_all_tests.py`.
- Run full test runner and verify 43 baseline + new tests all pass.
- Author all required M1 documentation deliverables.

---

## 4. Acceptance Criteria & Gate Verification

- [ ] All 43 baseline unit and integration tests pass without regression.
- [ ] Canonical URN correctly formats and parses namespaced objects (e.g., `urn:sap:bw:s21:200:adso:%2fCOMPANY%2fSALES:A`).
- [ ] Content fingerprint detects field schema modifications even if timestamps are identical.
- [ ] Single-writer queue processes concurrent multithreaded inputs without `SQLITE_BUSY` crashes.
- [ ] Database migrations execute cleanly on both empty in-memory/file databases and existing `bw_studio.sqlite`.
- [ ] Mutating HTTP verbs and forbidden SAP endpoints are rejected with `SecurityViolationError`.
- [ ] Benign RFC tests succeed in offline mock mode without requiring live SAP connection.
- [ ] Tarjan's SCC detects cycles, classifies edges, and preserves all original dependency edges.
- [ ] Zero unapproved Git commits or resets.
