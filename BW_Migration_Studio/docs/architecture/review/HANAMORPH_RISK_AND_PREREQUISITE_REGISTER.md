# HANAMORPH BW Migration & Modernization Studio
# Risk & Prerequisite Register — Architecture Blueprint 1.0 Review

**Document Reference:** `BW-MIG-RISK-2.0`  
**Status:** Approved Risk & Prerequisite Baseline  
**Classification:** SAP Enterprise Modernization Governance  
**Evaluation Date:** November 21, 2026  

---

## 1. Executive Risk Assessment

The HANAMORPH BW Migration Studio operates in complex, mission-critical enterprise environments. This register documents all identified technical, architectural, operational, security, and licensing risks, paired with authoritative mitigation strategies and explicit external prerequisites.

---

## 2. Comprehensive Risk Matrix

| Risk ID | Category | Description & Impact | Severity | Likelihood | Impacted Scope | Mitigation Strategy & Safeguards |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
| **RSK-01** | **Security / Compliance** | **Accidental Mutation of Source SAP S21:** The user `int_samarth` possesses unrestricted `SAP_ALL` privileges. Accidental writes could corrupt the reference landscape. | **CRITICAL** | Very Low | All Live S21 Connections | Enforce hardcoded HTTP verb whitelist (GET/HEAD only); eliminate write RFCs; mandate dedicated least-privilege user `Z_BW_MIGRATION_READ`. |
| **RSK-02** | **Architecture / SAP** | **BW Bridge abapGit Fallacy:** Assuming loose abapGit XML files can create ADSOs in BW Bridge leads to deployment failure. | **HIGH** | High | BW Bridge Target Route | Realign BW Bridge route to Pre-Conversion Readiness & ABAP Cloud routine wrapping; integrate with official Transfer Cockpit (`RSB4H`). |
| **RSK-03** | **Integration / API** | **Datasphere Task API Hallucination:** Relying on invented endpoints like `/api/v1/datasphere/tasks/*` breaks execution monitoring. | **HIGH** | High | Datasphere Ingestion Monitoring | Standardize on official `@sap/datasphere-cli` commands and direct Open SQL aggregate queries on target schemas. |
| **RSK-04** | **Data Integrity** | **Direct Change Log Extraction Hazard:** Reading `/BIC/AZSAM_SO012` directly bypasses locks, filters, and delta record-mode handling. | **HIGH** | Medium | Hybrid Coexistence Route | Eliminate direct DB table reading. Mandate official Operational Data Provisioning (ODP-BW) with Replication Flows. |
| **RSK-05** | **Scalability / IO** | **SQLite Single-Writer Concurrency Lock:** Parallel discovery workers simultaneously writing batches cause `SQLITE_BUSY` crashes. | **MEDIUM** | High | Level 2 Deep Discovery Engine | Implement Single-Writer Ingestion Queue (Producer-Consumer pattern); configure SQLite WAL mode with 10s busy timeout. |
| **RSK-06** | **Operational / UX** | **Approval Gate Fatigue:** 8 sequential manual approval gates cause administrative abandonment or careless rubber-stamping. | **MEDIUM** | High | Approval State Machine | Consolidate 8 gates into 4 logical enterprise governance milestones. |
| **RSK-07** | **System Stability** | **Dialog Process Starvation in Source BW:** High worker concurrency exhausts dialog work processes on production SAP BW instances. | **HIGH** | Low | Deep Discovery Sweeps | Enforce configurable per-source concurrency (1–4 threads); enforce dynamic 50ms–150ms jitter sleep intervals. |
| **RSK-08** | **Audit / Crypto** | **Weak Hashing & Compromised Signatures:** MD5 collision vulnerabilities and insecure HMAC key storage compromise compliance. | **MEDIUM** | Low | Audit & Change Detection | Mandate SHA-256 for all integrity hashing; derive HMAC keys via PBKDF2 with key version identifiers (`kid`). |

---

## 3. External Prerequisites & System Dependencies

The studio's capabilities are divided into:
1. **Local Autonomous Capabilities:** Fully functional offline or against cached fixtures without live SAP infrastructure.
2. **Enterprise Live Prerequisites:** Strictly contingent on external SAP landscape configuration and licensing.

### 3.1 Local Autonomous Capabilities (Zero External SAP Prerequisites)
- Offline metadata parsing (abapGit XML, JSON fixtures for `ZSAM_SO01` and `ZSAM_SO_CP`).
- Canonical Metadata Model construction, URN generation, and version tracking.
- Dependency DAG construction, Kahn's topological sort, and cycle breaking.
- 5D Feasibility scoring and decoupled confidence calculation.
- Target code generation: CSN 2.0 Local Tables, SQL DDL, Replication Flow JSON, and BTP ABAP Cloud routine wrappers.
- In-engine validation tiers (Levels 1 through 5).
- Delivery packaging, SHA-256 manifest sealing, and dry-run deployment script generation.

### 3.2 Enterprise Live Prerequisites Matrix

| Capability Scope | Required SAP System / Component | Minimum Release & Support Package | Network & Authorization Prerequisites | Licensing & Add-on Requirements |
| :--- | :--- | :--- | :--- | :--- |
| **Live ADT Discovery** | SAP BW 7.5 or SAP BW/4HANA | SAP_BW 750 SP08+ / DW4CORE 200+ | HTTPS Port 443 / 8000; Active SICF node `/sap/bc/adt`; Auth `S_ADT_RES` (ACTVT 03). | Standard SAP NetWeaver License. |
| **Live RFC Extraction** | SAP BW 7.5 on AnyDB/HANA | SAP_BASIS 740+ | TCP Port 3300; SAP NW RFC SDK (`sapnwrfc.dll`); Auth `S_RFC` (FUGR: `STFC_CONNECTION`, `RSO_*`). | Standard SAP NetWeaver License. |
| **SAP Datasphere Deployment** | SAP Datasphere Space | Current Cloud Release | Outbound HTTPS 443; OAuth2 Client Credentials from BTP subaccount; `@sap/datasphere-cli`. | SAP Datasphere Tenant & Space Quota. |
| **SAP BW Bridge Shell Transfer** | SAP BW Bridge on BTP | SAP BW Bridge 2021+ | SAP Cloud Connector reverse tunnel; RFC destination; SAP BW/4HANA Transfer Cockpit (`RSB4H`). | SAP BW Bridge Enterprise License; DMIS add-on on source BW. |
| **BDC Data Product Sharing** | SAP BW/4HANA & SAP Datasphere | BW/4HANA 2021 SP04+ or 2023 | SAP BW Cockpit Fiori configured; Data Sharing Cockpit enabled in Datasphere space. | SAP Business Data Cloud / Datasphere Enterprise Subscription. |
| **Hybrid ODP Delta Replication** | SAP BW 7.5 & Datasphere | SAP_BW 750 SP12+ | Active Operational Delta Queue (`ODQMON`); ODP-BW service enabled; Cloud Connector DP Agent. | SAP Datasphere Data Integration License. |
