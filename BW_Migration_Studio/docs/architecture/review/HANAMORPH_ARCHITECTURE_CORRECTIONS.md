# HANAMORPH BW Migration & Modernization Studio
# Architecture Corrections & Realignment Specification — Blueprint 1.0 Review

**Document Reference:** `BW-MIG-CORR-2.0`  
**Status:** Approved Architectural Corrections  
**Target Studio:** `BW_Migration_Studio/bw-studio`  
**Classification:** SAP Enterprise Modernization Architecture  
**Date:** November 21, 2026  

---

## 1. Overview of Required Architectural Corrections

Following the adversarial red-team audit of **Architecture Blueprint 1.0**, this document establishes nine mandatory architectural corrections. These corrections replace unverified assumptions, invented APIs, and unsupported SAP integration patterns with certified, production-grade enterprise architectures.

---

## 2. Correction 1: Source Connectivity & Non-Privileged Diagnostics

### Defect in Blueprint 1.0:
- Proposed `BAPI_USER_GET_DETAIL` for connection testing and `RFC_READ_TABLE` as the primary RFC metadata extractor.
- Assumed `RSOSM_CATALOG` exists and is populated for Level 1 catalog sweeps.

### Corrected Architecture:
1. **Benign Connection Diagnostic:** Replace `BAPI_USER_GET_DETAIL` with non-privileged, standard diagnostic RFCs:
   - `RFC_PING` (basic network/gateway handshake)
   - `STFC_CONNECTION` (echoes parameters and validates RFC session integrity without requiring user management authorizations).
2. **Elimination of Arbitrary `RFC_READ_TABLE`:**
   - In live network mode, metadata extraction must prioritize official **SAP ADT REST Services** (`/sap/bc/adt/bw/modeling/*`).
   - Where RFC is required, use dedicated read-only BW function modules or standard DDIC catalog views rather than generic `RFC_READ_TABLE`.
3. **Robust DDIC Catalog Sweeping:**
   - Decommission dependency on `RSOSM_CATALOG`.
   - Implement Level 1 catalog sweeps against official SAP Data Dictionary tables:
     - `RSOOBJECTS` (All BW repository objects with `OBJVERS = 'A'`)
     - `RSADSO` (Active ADSOs and properties)
     - `RSOCP` (Active CompositeProviders)
     - `RSTRAN` (Active Transformations)

---

## 3. Correction 2: Corrected Canonical URN Syntax & Identity

### Defect in Blueprint 1.0:
`urn:sap:bw:<system_id>:<object_type>:<technical_name>`  
*(Omitted client, namespace slashes, and object lifecycle version)*.

### Corrected Architecture:
The canonical URN syntax is updated to fully capture SAP multi-client, namespace, and version dimensions:

$$\mathbf{URN} = \mathbf{urn:sap:bw:}\langle \text{system\_id} \rangle \mathbf{:}\langle \text{client} \rangle \mathbf{:}\langle \text{object\_type} \rangle \mathbf{:}\langle \text{escaped\_name} \rangle \mathbf{:}\langle \text{version} \rangle$$

- **`system_id`:** SAP System Identifier (e.g., `s21`, `p01`).
- **`client`:** SAP 3-digit client (e.g., `200`, `100`).
- **`object_type`:** Canonical type code (`adso`, `hcpr`, `iobj`, `trfn`, `dtpa`, `elem`).
- **`escaped_name`:** URL-encoded technical name preserving customer namespaces (e.g., `/COMPANY/SALES_01` $\rightarrow$ `%2fCOMPANY%2fSALES_01`).
- **`version`:** Object lifecycle state (`A` = Active, `M` = Modified, `D` = Decommissioned).

**Example Canonical URNs:**
- Standard ADSO: `urn:sap:bw:s21:200:adso:zsam_so01:A`
- Namespaced CompositeProvider: `urn:sap:bw:s21:200:hcpr:%2fCORP%2fCP_SALES:A`
- Transformation: `urn:sap:bw:s21:200:trfn:00O2T4A9D382:A`

---

## 4. Correction 3: Realignment of SAP BW Bridge Strategy

### Defect in Blueprint 1.0:
- Claimed that generating loose abapGit XML files (`.adso.xml`) is a supported BW Bridge conversion mechanism.

### Corrected Architecture:
HANAMORPH realigns its BW Bridge route to its legitimate, high-value enterprise role: **Pre-Conversion Readiness & Remodeling Accelerator**:
1. **Readiness & Remediation Engine:**
   - Evaluates on-premise BW objects against official **SAP BW Bridge Feature Whitelists**.
   - Detects unsupported features (e.g., legacy InfoCubes, Classic DSOs, Virtual Providers, MultiProviders) and generates automated remodeling plans.
2. **ABAP Cloud Routine Transformation:**
   - Parses Start, End, and Field routines in legacy transformations.
   - Generates **BTP ABAP Cloud-compliant class wrappers** conforming to language version *ABAP for Cloud Development* (replacing obsolete database accesses and obsolete function modules).
3. **Transfer Cockpit Integration:**
   - Generates shell conversion metadata descriptors and transfer scoping files formatted for ingestion into the **SAP BW/4HANA Transfer Cockpit (`RSB4H`)**, allowing developers to run the official SAP conversion tooling seamlessly.

---

## 5. Correction 4: Realignment of SAP Datasphere API Contracts

### Defect in Blueprint 1.0:
- Hallucinated non-existent endpoints such as `/api/v1/datasphere/tasks/*` for monitoring replication flows.

### Corrected Architecture:
1. **Documented CLI Integration:**
   - HANAMORPH standardizes deployment execution on the official **`@sap/datasphere-cli`**:
     ```bash
     # Object Validation (Level 6 Dry-Run)
     datasphere objects validate --space <SPACE_ID> --file-path <PATH_TO_CSN>
     
     # Object Deployment
     datasphere objects import --space <SPACE_ID> --file-path <PATH_TO_CSN>
     ```
2. **Official REST API Endpoints:**
   - Where HTTP APIs are invoked, HANAMORPH restricts calls to the official **SAP Datasphere Core Service API**:
     - `GET /dwaas-core/api/v1/spaces` (Space discovery and quota validation)
     - `GET /dwaas-core/api/v1/spaces/{spaceId}/connections` (Connection verification)
3. **Replication Monitoring Scope:**
   - Ingestion monitoring is performed via documented SAP BTP Application Logging APIs or by querying target table metadata via SAP HANA Cloud Open SQL schemas (`SELECT COUNT(*)`), eliminating dependency on invented endpoints.

---

## 6. Correction 5: Realignment of BDC & Data Product Generation

### Defect in Blueprint 1.0:
- Cited private, internal kernel class `CL_RSO_DATA_PRODUCT` as a direct public integration API.

### Corrected Architecture:
1. **Declarative Open Data Product Manifests:**
   - HANAMORPH generates standard, declarative **`data-product.json`** descriptor files conforming to the SAP Open Data Product specification:
     - Domain, Data Product Name, Version, Owner
     - SLA, Freshness, and Data Contract definitions
     - Input/Output port bindings to SAP Datasphere Analytic Models and Views
2. **Explicit Administrative Dependencies:**
   - The architecture explicitly documents that physical **BW Data Subscription** activation requires administrator configuration within the **SAP BW Cockpit (Fiori)** on supported releases (BW/4HANA 2021/2023).

---

## 7. Correction 6: Hybrid Replication via Certified ODP-BW

### Defect in Blueprint 1.0:
- Specified direct database table extraction against Change Log tables (`/BIC/AZSAM_SO012`).

### Corrected Architecture:
1. **Certified ODP Extraction:**
   - All hybrid replication flows generated by HANAMORPH target the **SAP Operational Data Provisioning (ODP-BW)** framework.
   - Standard ADSOs are exposed as ODP InfoProviders (`RODPS_BW_INFO_PROVIDER`).
2. **Native Delta Management:**
   - SAP Datasphere Replication Flows connect to the ODP context via Cloud Connector.
   - The source SAP NetWeaver system manages delta extraction queues safely via the **Operational Delta Queue (`ODQMON`)**, guaranteeing ACID compliance, record-mode translation (After-Images, Before-Images, Deletes), and application-level authorization.

---

## 8. Correction 7: Concurrency & Storage Ingestion Architecture

### Defect in Blueprint 1.0:
- Fixed 4-worker threading declared universally safe; multiple threads writing concurrently to SQLite cause database lock errors.

### Corrected Architecture:
1. **Configurable Dynamic Concurrency:**
   - Worker concurrency is dynamically configured per connection (default: 2 threads for production systems; up to 6 for benchmark/dev systems).
   - Jittered sleep intervals adapt dynamically based on SAP response latency.
2. **Single-Writer Ingestion Queue Pattern:**
   - Parallel extraction workers place normalized canonical entities into a thread-safe in-memory queue (`queue.Queue`).
   - A single, dedicated **Database Ingestion Worker** flushes records to SQLite in transactions of 1,000 items, completely eliminating `SQLITE_BUSY` database lock collisions.

---

## 9. Correction 8: Consolidated 4-Milestone Governance & Cryptographic Hardening

### Defect in Blueprint 1.0:
- 8 separate approval gates create administrative fatigue; HMAC keys lack lifecycle and rotation specifications; MD5 was used for change detection.

### Corrected Architecture:
1. **4 Logical Enterprise Governance Milestones:**
   - **Milestone Gate 1: Scope & Discovery Baseline**
   - **Milestone Gate 2: Architecture & Strategy Allocation**
   - **Milestone Gate 3: Generation & Technical Verification**
   - **Milestone Gate 4: Reconciliation & Production Cutover**
2. **Cryptographic Hardening:**
   - Mandatory **SHA-256** for all snapshot comparison, file integrity, and audit hashes.
   - HMAC signing keys are derived via PBKDF2 (100,000 iterations) from an environment master key, with key version identifiers (`kid`) recorded in `audit_approvals`.
