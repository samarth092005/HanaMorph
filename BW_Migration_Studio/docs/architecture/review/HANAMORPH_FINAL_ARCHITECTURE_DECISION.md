# HANAMORPH BW Migration & Modernization Studio
# Final Architecture Decision Record — Phase 2.1 Reconciled Baseline

**Document Reference:** `BW-MIG-DEC-2.1`  
**Status:** Authoritative Architectural Determination  
**Review Target:** Blueprint 1.0, Review 2.0, and Evidence Reconciliation 2.1  
**Lead Reviewer:** Independent SAP Enterprise Architect, BW/4HANA Migration Specialist & Security Auditor  
**Date:** November 21, 2026  

---

## 1. Final Architecture Determination

> [!IMPORTANT]
> ### FINAL VERDICT: APPROVED FOR M1 WITH CONDITIONS
> 
> Following the comprehensive Phase 2.1 Evidence Reconciliation, the architectural baseline for **Milestone M1 (Phase A: Core Foundations, Schemas & Benign Connectivity)** is formally approved.
> 
> Milestone M1 entails zero risk to live SAP infrastructure, introduces zero mutating operations, requires zero external cloud subscriptions, and is 100% implementable and testable in the local workstation environment.

---

## 2. Seven-Point Architectural Reconciliation

### 2.1 Which Parts of Blueprint 1.0 Remain Valid?
1. **The Metadata Modernization Invariant:** The core principle that HANAMORPH operates exclusively on metadata and logic while delegating bulk business data movement to SAP-native replication engines remains the foundational cornerstone.
2. **Strict Read-Only Isolation for SAP S21:** The hardcoded HTTP `GET`/`HEAD` verb whitelist, blocking of CTS transport generation, and display-only DDIC inspection remain non-negotiable security mandates.
3. **The 8-Tab UX / Product Journey:** The workflow mapping across the existing 8-tab frontend interface (Connect $\rightarrow$ Configure $\rightarrow$ Discover $\rightarrow$ Assess $\rightarrow$ Plan $\rightarrow$ Approve $\rightarrow$ Generate $\rightarrow$ Deliver) is preserved without UI breakage.
4. **Core Target Model Synthesizers:** The underlying generation logic in `datasphere.py` for CSN 2.0 Local Tables (`type: "entity"`), Views (`type: "view"`), and HANA Column Tables DDL is confirmed architecturally sound.
5. **Delivery Packaging & Sealed Bundles:** The ZIP packager, SHA-256 manifest sealing, and dry-run script scaffolding in `packager.py` remain production-ready.

---

### 2.2 Which Review 2.0 Corrections Are Accepted?
1. **Benign Diagnostic RFCs (CORR-1):** Replacement of `BAPI_USER_GET_DETAIL` with standard, unprivileged `RFC_PING` and `STFC_CONNECTION`.
2. **Corrected Canonical URN Syntax (CORR-2):** Incorporation of client (`MANDT`), URL-escaped namespaces, and object version (`OBJVERS`):  
   `urn:sap:bw:<system>:<client>:<type>:<escaped_name>:<version>`.
3. **Single-Writer SQLite Ingestion Queue (CORR-7):** Decoupling parallel extraction workers from SQLite transactions via `queue.Queue` to prevent `SQLITE_BUSY` concurrency locks.
4. **Four-Milestone Enterprise Governance (CORR-8):** Consolidation of 8 manual gates into 4 logical milestones with PBKDF2 HMAC-SHA256 tamper-evident signing.
5. **Cryptographic Hardening (CORR-9):** Strict replacement of deprecated MD5 with SHA-256 for all snapshot comparison, file integrity, and audit signatures.
6. **Rejection of Direct Change Log SQL Reads (CORR-6):** Formal prohibition of direct database queries on `/BIC/A*2` change log tables in favor of certified Operational Data Provisioning (ODP-BW).

---

### 2.3 Which Review 2.0 Claims Are Withdrawn or Revised?
1. **Withdrawal of "Datasphere Task API is Invented":** Review 2.0 incorrectly stated that the Tasks API was invented. It is affirmed that SAP Datasphere publishes an official, standard **Task API** (Task Chains REST API) on the SAP Business Accelerator Hub for triggering runs, checking run status, retrying, and canceling task chains.
2. **Revision of BW Bridge Conversion Tooling:** Review 2.0 oversimplified shell conversion by citing `RSB4H` alone. The architecture is revised to specify transaction **`RSB4HTW`** (Transfer to BW Bridge / Cloud) in SAP BW 7.5 paired with the **BW Bridge Transfer Cockpit** in Eclipse BW Modeling Tools (BWMT).
3. **Revision of BDC Data Product Automation:** Review 2.0 proposed `data-product.json` as an automated output. It is clarified that while HANAMORPH generates declarative `data-product.json` manifests for documentation and governance, actual data product publication in the SAP Data Sharing Cockpit is an un-automatable **`MANUAL_ADMIN_ACTION`**.
4. **Correction of Tarjan's SCC Role:** Review 2.0 described Tarjan's SCC as a "cycle resolver". It is clarified that Tarjan detects SCCs, while explicit edge decoupling (`PRIMARY_DATA_FLOW` vs. `LOOKUP_DEPENDENCY`) is required to break cycles before Kahn's topological sort can execute.

---

### 2.4 Which Capabilities Can Be Implemented Locally (Zero SAP Access)?
The following core capabilities can be implemented and fully verified locally using cached test fixtures:
- SQLite WAL mode and the Single-Writer Ingestion Queue.
- Canonical Metadata Model entity classes and the corrected URN generator.
- Kahn's DAG builder with SCC cycle detection and edge decoupling.
- 5D Feasibility assessment engine and decoupled confidence scoring.
- Target generators: CSN 2.0 Local Tables, Views, Analytic Models (`CUBE`), and Replication Flow JSON.
- BW Bridge Pre-Conversion Readiness analyzer and BTP ABAP Cloud routine wrappers.
- Declarative BDC Open Data Product manifest generator (`data-product.json`).
- In-engine validation tiers (Levels 1 through 5: syntax, data types, semantics, graph closure, CDC mode).
- Delivery Packager, SHA-256 manifest sealing, and dry-run deployment script generators.

---

### 2.5 Which Capabilities Require Live SAP Infrastructure or Licensing?
The following capabilities are strictly contingent on live external infrastructure and administrator credentials:
- Live ADT deep extraction via HTTPS 443 / 8000 (`S_ADT_RES`).
- Live RFC diagnostic pings via TCP 3300 (`sapnwrfc.dll`).
- Live BW Bridge shell conversion execution (requires SAP Note 3141688, `RSB4HTW`, Cloud Connector, and BW Bridge tenant).
- Physical BW Data Subscription activation (requires SAP BW Cockpit on BW/4HANA 2021/2023).
- Live Datasphere deployment and Level 6 dry-run (requires `@sap/datasphere-cli` and space OAuth2 credentials).
- Level 7 physical data reconciliation proofs (requires Open SQL schema access via `hdbcli`).

---

### 2.6 Target Route Readiness Summary

| Target Route | Implementation Readiness | Architectural Classification | Execution Mechanism |
| :--- | :--- | :--- | :--- |
| **Route 1: Native SAP Datasphere** | **READY FOR IN-ENGINE IMPLEMENTATION** | Automated Target Generation | CSN 2.0 schemas, SQL DDL, and Replication Flow JSON emitted directly. Deployed via `@sap/datasphere-cli`. |
| **Route 2: SAP BW Bridge** | **READY FOR PRE-CONVERSION ACCELERATION** | Advisory & Code Wrapping | Emits BTP ABAP Cloud routine wrappers and shell transfer descriptors. Shell conversion executed via `RSB4HTW`. |
| **Route 3: SAP BDC Data Product** | **ADVISORY SPECIFICATION ONLY** | Advisory Runbook & Manifest | Emits declarative `data-product.json`. Live publication is classified as `MANUAL_ADMIN_ACTION` in Datasphere UI. |
| **Route 4: Hybrid Coexistence** | **READY FOR REPLICATION SPECIFICATION** | Controlled ODP Coexistence | Emits ODP-BW Replication Flow configurations (`ODQMON`). Direct change log database reading is prohibited. |

---

## 3. Explicit Conditions for Milestone M1 Implementation

Engineering implementation of **Milestone M1 (Phase A)** may proceed strictly under the following four conditions:

1. **Condition 1 (Baseline Preservation):** All 43 automated tests in `BW_Migration_Studio/bw-studio/tests/run_all_tests.py` must continue to execute and pass 100% green without regression.
2. **Condition 2 (Zero Mutating S21 Calls):** The connection manager must enforce the strict read-only HTTP verb jail (allowing only `GET` and `HEAD`), with RFC testing limited strictly to benign diagnostic calls (`RFC_PING`, `STFC_CONNECTION`).
3. **Condition 3 (Corrected Identity Schema):** The canonical database schema must adopt the corrected URN format (`urn:sap:bw:<system>:<client>:<type>:<escaped_name>:<version>`) and implement the Single-Writer Ingestion Queue.
4. **Condition 4 (Scope Containment):** Implementation during Milestone M1 is restricted to core foundations, storage hardening, canonical schemas, and benign connectivity handlers. No target deployment code or live cloud calls may be executed.

---

### Formal Sign-Off
- **Architectural Baseline:** Approved for Milestone M1.
- **Review Status:** Reconciled, documented, and sealed.
- **Next Permitted Step:** Phase A / Milestone M1 implementation upon explicit human instruction.
