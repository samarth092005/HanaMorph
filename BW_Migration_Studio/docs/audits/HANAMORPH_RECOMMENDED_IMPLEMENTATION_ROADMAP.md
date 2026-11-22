# HANAMORPH BW MIGRATION STUDIO — RECOMMENDED IMPLEMENTATION ROADMAP

**Document Version:** 1.0.0  
**Date:** 2026-11-21  
**Project:** HANAMORPH — Enterprise SAP BW Modernization Product  
**Audit Reference:** `docs/audits/HANAMORPH_CURRENT_STATE_AUDIT.md`  
**Gap Analysis Reference:** `docs/audits/HANAMORPH_GAP_ANALYSIS.md`  

---

## 1. Executive Implementation Strategy

The HANAMORPH BW Migration Studio has achieved a robust local foundation: discovery of standard BW objects, Kahn's topological sequencing, 5D assessment scoring, CSN/DDL generation for Native Datasphere, 7-level validation, and sealed delivery packaging.

To evolve this local tool into an **enterprise-grade, production-ready product**, engineering must address four foundational capability gaps:
1. **Multi-Route Generation**: Building true artifact generators for SAP BW Bridge, BDC Data Products, and Datasphere Replication Flows.
2. **Deep BW Metadata Extraction**: Parsing transformation routines (TRFN), DTPs, and Process Chains rather than relying on high-level heuristics.
3. **Enterprise Platform Architecture**: Packaging for SAP BTP Cloud Foundry with MTA descriptors, XSUAA security, and asynchronous job queues.
4. **End-to-End Live Tenant Testing**: Establishing automated integration testing against live SAP Datasphere spaces.

---

## 2. Phased Implementation Roadmap

```
+-----------------------------------------------------------------------------------+
|                     HANAMORPH ROADMAP EXECUTION PHASES                            |
+-----------------------------------------------------------------------------------+
|  PHASE A: Multi-Route Target Modernization Engines                                |
|  • Build SAP BW Bridge Package Generator (abapGit XML + BTP ABAP manifest)        |
|  • Build BDC Data Product Generator (ODP manifests + Data Contract SLAs)          |
|  • Build Datasphere Replication Flow Generator (.flow.json)                       |
|  • Build Hybrid Coexistence Dual-Run Replication Specs                            |
+-----------------------------------------------------------------------------------+
|  PHASE B: Advanced BW Metadata Discovery & Parsing                                |
|  • Implement Transformation (TRFN) Rule & Routine Parser (Start/End/Field)        |
|  • Implement Data Transfer Process (DTP / RSBKDTP) Metadata Extractor             |
|  • Implement Process Chain (RSPC) Extraction & Lineage Engine                     |
|  • Implement Delta Behaviour & Change Log CDC Mapping                             |
+-----------------------------------------------------------------------------------+
|  PHASE C: Enterprise Runtime & BTP Cloud Foundry Deployment                       |
|  • Package MTA descriptor (mta.yaml), manifest.yml, requirements.txt, Procfile   |
|  • Implement Asynchronous Worker Engine for migration_jobs & job_logs             |
|  • Integrate SAP BTP XSUAA Service for JWT token validation and RBAC              |
|  • Wire formal audit event emission into audit_events table                       |
+-----------------------------------------------------------------------------------+
|  PHASE D: Governance, Fiori Integration & Live Tenant Testing                     |
|  • Reconcile runtime data via row-count & hash comparison against target          |
|  • Integrate UI5 frontend components into main HANAMORPH Launchpad                |
|  • Execute live target end-to-end testing against SAP Datasphere test space       |
+-----------------------------------------------------------------------------------+
```

---

## 3. Detailed Work Breakdown Structure

### Phase A: Multi-Route Target Modernization Engines (Weeks 1–3)
- **Task A.1 (BW Bridge Generator)**:
  - Create `generation_engine/bridge_generator.py`.
  - Generate abapGit XML folder structure for target ADSOs and InfoObjects.
  - Generate BTP ABAP environment RFC destination configuration.
  - Package preserved procedural ABAP classes for deployment into BW Bridge tenant.
- **Task A.2 (BDC Data Product Generator)**:
  - Create `generation_engine/bdc_generator.py`.
  - Generate Open Data Protocol (ODP) data product descriptor (`data-product.json`).
  - Generate business context metadata, SLA definitions, and schema contract.
  - Generate consumption entitlement rules.
- **Task A.3 (Datasphere Replication Flow Generator)**:
  - Create `generation_engine/flow_generator.py`.
  - Generate `.flow.json` specifying source connection, container, projection, and load mode (`Initial Only` vs `Initial and Delta`).
  - Wire flow generation into `GenerationEngine.generate_for_plan`.
- **Task A.4 (Hybrid Coexistence Specification Generator)**:
  - Create `generation_engine/hybrid_generator.py`.
  - Generate dual-run architecture specification, cutover checklist, and delta reconciliation rules.

---

### Phase B: Advanced BW Metadata Discovery (Weeks 4–6)
- **Task B.1 (Transformation & Routine Parser)**:
  - Create `discovery/transformation_parser.py`.
  - Ingest `RSTRAN` / `RSTRANRULE` metadata or cached transformation models.
  - Extract rule types (`DIRECT`, `ROUTINE`, `FORMULA`, `CONSTANT`, `INITIAL`).
  - Parse ABAP routines and assess complexity for automated SQL rewrite or Bridge preservation.
- **Task B.2 (DTP & Process Chain Extractor)**:
  - Create `discovery/dtp_parser.py` and `discovery/process_chain_parser.py`.
  - Ingest `RSBKDTP` (extraction mode, package size, error limit).
  - Ingest `RSPCPROCESS` (chain sequence, trigger events, variant names).
  - Expand dependency graph with process chain orchestration nodes.
- **Task B.3 (Delta & CDC Analysis Engine)**:
  - Map source delta capability (ODP delta queues vs ADSO change log extraction).
  - Tag each target flow with appropriate load mode and CDC method.

---

### Phase C: Enterprise Runtime & BTP Cloud Foundry Deployment (Weeks 7–8)
- **Task C.1 (BTP Cloud Foundry Packaging)**:
  - Create `mta.yaml` declaring application router, backend service, and XSUAA security.
  - Create `manifest.yml` for standalone Cloud Foundry push (`python_buildpack`).
  - Create `requirements.txt` with locked dependency versions.
  - Create `Procfile` specifying web entrypoint: `web: python backend/server.py`.
- **Task C.2 (Asynchronous Job Queue & Log Streaming)**:
  - Implement worker queue for long-running discovery, generation, and validation tasks.
  - Return `202 Accepted` with job tracking URL (`/api/jobs/<job_id>`).
  - Populate `migration_jobs` and `job_logs` in SQLite.
  - Add Server-Sent Events (SSE) endpoint for real-time progress streaming in UI.
- **Task C.3 (Enterprise Security & Audit Trails)**:
  - Integrate JWT / OAuth bearer token verification using `@sap/xssec` or Python equivalent.
  - Emit structured audit records into `audit_events` on plan approval, generation, and packaging.

---

### Phase D: Governance, Fiori Integration & Live Tenant Testing (Weeks 9–10)
- **Task D.1 (Runtime Data Reconciliation)**:
  - Implement `validation_engine/data_reconciliation.py`.
  - Generate row-count and aggregate key-figure comparison queries for source and target.
- **Task D.2 (Fiori Launchpad UI Integration)**:
  - Convert `frontend/index.html` into a modular SAPUI5 Component (`Component.js`, XML views) matching the main HANAMORPH platform aesthetic.
- **Task D.3 (Live Tenant Automated Integration Testing)**:
  - Execute end-to-end dry-run deployment using `@sap/datasphere-cli` in a sandbox space (`SALES_ANALYTICS`).

---

## 4. Immediate Action Items (Sprint 1 Priorities)

1. **Create `requirements.txt` and `Procfile`**: Ensure deterministic Python environment and Cloud Foundry compatibility.
2. **Implement Replication Flow Generator (`flow_generator.py`)**: Generate `.flow.json` alongside CSN and DDL.
3. **Implement BW Bridge Package Generator (`bridge_generator.py`)**: Produce genuine abapGit conversion bundles for ABAP-heavy objects.
4. **Implement BDC Data Product Generator (`bdc_generator.py`)**: Produce ODP data product descriptors.
5. **Wire Asynchronous Job Tracking**: Activate `migration_jobs` and `job_logs` tables so UI displays live progress bars.
