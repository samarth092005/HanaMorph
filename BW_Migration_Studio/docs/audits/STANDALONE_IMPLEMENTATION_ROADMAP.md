# BW MIGRATION STUDIO — STANDALONE IMPLEMENTATION ROADMAP
**Roadmap Version:** 1.0.0 (Post M2–M3 Baseline)  
**Scope:** Standalone Product Maturation & Production Readiness  
**Target Architecture:** Autonomous SAP BW Modernization Platform  

---

## 1. Roadmap Overview

The BW Migration Studio has proven its core functionality across discovery, 7D complexity scoring, 4-route assessment, dependency DAG sequencing, artifact generation, and 7-level validation.

To advance from an engineering baseline to an enterprise-grade standalone modernization tool, the following four development milestones are scheduled:

```
+--------------------------------------------------------------------------------+
|                     STANDALONE PRODUCT ROADMAP (M4.1 - M4.4)                   |
+--------------------------------------------------------------------------------+

  [ SPRINT M4.1: RUNTIME ARCHITECTURE & CONCURRENCY HARDENING ]
  - Consolidate database files to canonical database/bw_studio.sqlite.
  - Upgrade backend/server.py to ThreadingTCPServer to enable non-blocking request handling.
  - Introduce requirements.txt and pyproject.toml package manifests.
  -------------------------------------------------------------------------------
  [ SPRINT M4.2: SECURITY HARDENING & AUDIT TRAIL ]
  - Add API Token middleware (Authorization: Bearer <token>) on all REST routes.
  - Implement api_request_logs table in SQLite tracking request timestamps and actions.
  - Add request rate limiting and payload size verification.
  -------------------------------------------------------------------------------
  [ SPRINT M4.3: ADVANCED CSN 2.0 & AUTOMATED ZIP PACKAGING ]
  - Extend csn_generator.py to generate full Datasphere Space packages.
  - Add support for Datasphere Data Transformation Flow JSON specifications.
  - Upgrade delivery_packager.py to produce sealed, compressed .zip archives.
  -------------------------------------------------------------------------------
  [ SPRINT M4.4: UI MODULARIZATION & VISUAL LINEAGE GRAPH ]
  - Modularize frontend/index.html into separate HTML, CSS, and JS assets.
  - Implement interactive SVG/Canvas node-link graph for multi-hop lineage visualization.
  - Provide interactive drag-and-drop sequencing in Migration Plan view.
```

---

## 2. Milestone Work Breakdown Structure

### Milestone M4.1: Runtime Architecture & Concurrency Hardening
- **Objective:** Eliminate runtime bottlenecks and unify persistence paths.
- **Tasks:**
  1. Update `tests/verify_synthetic_e2e.py` to use `database/bw_studio.sqlite`.
  2. Update `backend/server.py` to inherit from `socketserver.ThreadingTCPServer`.
  3. Create `requirements.txt` declaring `cryptography>=41.0.0` and Python 3.10+ prerequisites.
  4. Verify all 79 tests continue to pass.

### Milestone M4.2: Security Hardening & Audit Trail
- **Objective:** Lock down backend REST interface and provide an auditable request log.
- **Tasks:**
  1. Add `STUDIO_API_TOKEN` to `BW_Migration_Studio/.env.example`.
  2. Implement authorization header inspection in `server.py:do_GET` and `do_POST`.
  3. Create Migration 8 in `database/schema_manager.py` for `api_request_logs`.
  4. Write automated tests in `tests/test_server_live.py` verifying unauthorized requests receive HTTP 401.

### Milestone M4.3: Advanced Target Generation & ZIP Packaging
- **Objective:** Produce enterprise-ready Datasphere deployment packages.
- **Tasks:**
  1. Expand `csn_generator.py` to generate complete Datasphere Space model packages with calculation variables.
  2. Add automated `.zip` archive generation with SHA-256 integrity seal in `delivery_packager.py`.
  3. Add automated test verifying `.zip` package extraction and checksum match.

### Milestone M4.4: UI Modularization & Visual Lineage Graph
- **Objective:** Transform the monolithic UI into a scalable, interactive visualization suite.
- **Tasks:**
  1. Decompose `index.html` into clean static assets under `frontend/css/`, `frontend/js/`, and `frontend/views/`.
  2. Integrate a visual SVG DAG rendering component on Screen 5 for interactive blast radius inspection.
  3. Add wave reordering controls to Screen 11.
