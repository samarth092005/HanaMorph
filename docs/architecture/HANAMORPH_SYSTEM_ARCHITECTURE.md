# HANAMORPH BW Migration & Modernization Studio
# System Architecture & Component Decomposition — Architecture Blueprint 1.0

**Document Reference:** `BW-MIG-SYS-1.0`  
**Status:** Approved for Architecture Design  
**Target Studio:** `BW_Migration_Studio/bw-studio`  
**Classification:** SAP Enterprise Modernization Architecture  

---

## 1. High-Level System Architecture

The HANAMORPH system is architected as a modular, decoupled, event-ready application designed for local desktop development and enterprise cloud deployment (SAP BTP Cloud Foundry). 

### Diagram 1: Overall System Architecture

```mermaid
flowchart TB
    subgraph PRESENTATION_LAYER["Presentation & UX Layer (Modern UI / Web Components)"]
        UI_TAB1["Tab 1: Connection & Source Config"]
        UI_TAB2["Tab 2: Landscape Inventory"]
        UI_TAB3["Tab 3: Deep Discovery Explorer"]
        UI_TAB4["Tab 4: Lineage & Assessment"]
        UI_TAB5["Tab 5: Migration Strategy Planner"]
        UI_TAB6["Tab 6: HITL Approval Governance"]
        UI_TAB7["Tab 7: Target Generation & Validation"]
        UI_TAB8["Tab 8: Delivery & Deployment Bundler"]
    end

    subgraph API_GATEWAY["API Gateway & Request Router (FastAPI / Modular Router)"]
        AUTH_MW["Security & Auth Middleware (XSUAA / Token / Path Jail)"]
        RATE_MW["Rate Limiter & Source Load Protector"]
        ROUTER["REST API Dispatcher (/api/v1/bw/*)"]
    end

    subgraph ENGINE_CORE["HanaMorph Modernization Engine Core"]
        DISC_ENG["Discovery Engine\n(L1 Inventory & L2 Deep Analyzer)"]
        INTEL_ENG["Intelligence Engine\n(DAG Lineage & 5D Assessment)"]
        PLAN_ENG["Planning & Wave Orchestrator\n(Route Allocator & Sizing)"]
        APPROVAL_ENG["Approval State Machine\n(HITL Gate Enforcement)"]
        GEN_ENG["Target Artifact Generator\n(Datasphere / Bridge / BDC / Hybrid)"]
        VAL_ENG["Multi-Tier Validation Framework\n(7-Level Verification)"]
        DELIV_ENG["Delivery Packager\n(Zip Bundler & Dry-Run CLI)"]
    end

    subgraph METADATA_ABSTRACTION["Source Connectivity Gateway (Strict Read-Only)"]
        BW_CONN["BW Connection Manager\n(PyRFC / ADT REST / Offline Parser)"]
        DSP_CONN["Datasphere Connection Manager\n(CLI & Metadata API)"]
        BTP_CONN["BTP & HANA Connection Manager\n(Service Keys & Destinations)"]
    end

    subgraph STORAGE_LAYER["Persistence & Repository Layer"]
        CANON_DB[("Canonical Metadata Repository\n(URN Models & Schemas)")]
        PROJ_DB[("Project & Wave State DB\n(Config, Waves, Plans)")]
        JOB_DB[("Asynchronous Job Queue\n(State, Logs, Checkpoints)")]
        AUDIT_DB[("Immutable Audit & Evidence DB\n(Signatures, Validations)")]
        ARTIFACT_STORE[("Target Artifact File Store\n(CSN, SQL, JSON, XML)")]
    end

    subgraph EXTERNAL_REPLICATION["External SAP Bulk Data Fabric (Out-of-Process)"]
        DSP_REP["SAP Datasphere Replication Flows\n(Native CDC / Change Log)"]
        SAP_SLT["SAP Landscape Transformation / DI"]
        BW_ODP["SAP ODP / Data Subscriptions"]
    end

    %% Presentation to Gateway
    PRESENTATION_LAYER -->|HTTP / JSON (REST)| AUTH_MW
    AUTH_MW --> RATE_MW
    RATE_MW --> ROUTER

    %% Gateway to Engine Core
    ROUTER --> DISC_ENG
    ROUTER --> INTEL_ENG
    ROUTER --> PLAN_ENG
    ROUTER --> APPROVAL_ENG
    ROUTER --> GEN_ENG
    ROUTER --> VAL_ENG
    ROUTER --> DELIV_ENG

    %% Engine to Connectivity
    DISC_ENG --> BW_CONN
    GEN_ENG --> DSP_CONN
    DELIV_ENG --> BTP_CONN

    %% Engine to Storage
    DISC_ENG <--> CANON_DB
    INTEL_ENG <--> CANON_DB
    PLAN_ENG <--> PROJ_DB
    APPROVAL_ENG <--> AUDIT_DB
    GEN_ENG --> ARTIFACT_STORE
    VAL_ENG <--> AUDIT_DB
    ENGINE_CORE <--> JOB_DB

    %% Generation to External Orchestration (Manifests Only)
    GEN_ENG -.->|Flow Manifests (.flow.json)| DSP_REP
    GEN_ENG -.->|Data Product Manifests| BW_ODP

    classDef readonly fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef storage fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef external fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,stroke-dasharray: 5 5;
    class BW_CONN,METADATA_ABSTRACTION readonly;
    class STORAGE_LAYER,CANON_DB,PROJ_DB,JOB_DB,AUDIT_DB,ARTIFACT_STORE storage;
    class EXTERNAL_REPLICATION,DSP_REP,SAP_SLT,BW_ODP external;
```

---

## 2. Component Decomposition & Functional Responsibilities

### 2.1 Presentation & UI Layer
- Implemented as modern vanilla web components and responsive HTML/CSS/JS without heavy runtime frameworks, ensuring minimal attack surface and instantaneous rendering.
- Maps one-to-one with the eight functional stages of the migration lifecycle.
- Uses RESTful JSON polling and server-sent state updates to track background jobs without freezing the user interface.

### 2.2 API Gateway & Request Dispatcher
- Provides centralized authentication, path traversal protection, and strict input validation.
- Enforces strict read-only guarantees on any outbound SAP network interaction.
- Bridges synchronous user actions (e.g., viewing an assessment) and long-running asynchronous batch tasks (e.g., deep discovery of an entire InfoArea).

### 2.3 The Core Modernization Engines
1. **Discovery Engine (`discovery.py`):**
   - Decoupled into Level 1 (Lightweight Inventory) and Level 2 (Selective Deep Discovery).
   - Normalizes disparate source inputs (ADT REST XML, RFC table reads, and offline cache files) into a common format.
2. **Intelligence & Lineage Engine (`assessment.py`):**
   - Constructs a Directed Acyclic Graph (DAG) of the entire BW data warehousing layer.
   - Computes 5-dimensional feasibility scores ($S_{total}$) and distinct confidence metrics ($C_{total}$).
   - Detects transformation routine complexity and flag redesign requirements.
3. **Planning & Strategy Engine:**
   - Evaluates target fit across Native Datasphere, BW Bridge, BDC, and Hybrid.
   - Groups objects into topological waves based on dependency depth.
4. **Approval & Governance Engine:**
   - Manages state machine transitions from `DISCOVERED` to `CUTOVER_READY`.
   - Requires explicit human sign-off at critical architecture and deployment boundaries.
5. **Generation Engine (`datasphere.py`, `bridge.py`, `bdc.py`):**
   - Produces native CSN 2.0 schemas, HANA Column Tables & Views DDL, Replication Flow definitions, abapGit XML packages, and BDC Data Product descriptors.
6. **Validation Engine (`validation.py`):**
   - Implements a 7-tier verification pipeline checking syntax, schema, semantics, currency/unit integrity, and external data reconciliation proofs.
7. **Delivery Packager (`packager.py`):**
   - Bundles all generated code, schemas, deployment shell scripts, validation evidence, and runbooks into a single versioned `.zip` artifact.

---

## 3. The Core Invariant: Metadata vs. Bulk Business Data

| Dimension | HANAMORPH In-Process Engine | SAP Native Data Replication (Out-of-Process) |
| :--- | :--- | :--- |
| **Object Types Handled** | DDIC definitions, ADSO metadata, Join conditions, Transformation formulas, DTP settings. | Actual business transactions, customer records, general ledger line items, billing history. |
| **Data Volume Scale** | Kilobytes to Megabytes (100,000 metadata objects $\approx$ 150MB). | Gigabytes to Terabytes (10,000,000+ line items). |
| **Processing Node** | Local Python runtime or BTP Cloud Foundry application container. | SAP Datasphere DP Agent, SAP HANA Smart Data Integration, SAP Landscape Transformation. |
| **Network Protocols** | HTTPS (ADT REST GET), RFC (BAPI read-only). | RFC Data Pumping, WebSocket CDC streaming, HANA JDBC / DP Agent streams. |
| **Security & Privacy Risk** | Minimal (contains technical data models; zero PII / GDPR transactional data). | High (contains sensitive financial, HR, and customer records; handled by SAP security). |

> [!CAUTION]
> **Architectural Guardrail:** Any attempt to implement a generic Python extractor that dumps business records from tables like `/BIC/AZSAM_SO012` into local CSV, Parquet, or SQLite will fail enterprise architecture review. HANAMORPH produces the Replication Flow JSON contracts that instruct SAP Datasphere how to execute the high-speed data movement directly from SAP BW.

---

## 4. Multi-Tenant and Progressive Storage Strategy

1. **Local Workstation Mode (Single-Tenant Developer):**
   - Persistence backed by file-based SQLite 3 with Write-Ahead Logging (WAL) enabled (`PRAGMA journal_mode = WAL;`).
   - Artifacts stored on the local filesystem within an isolated workspace directory (`BW_Migration_Studio/bw-studio/output/`).
2. **SAP BTP Cloud Foundry Mode (Multi-Tenant Enterprise):**
   - Metadata persistence backed by SAP HANA Cloud or Managed PostgreSQL on SAP BTP.
   - Artifacts stored in SAP BTP Object Store (S3-compatible / Azure Blob) with client tenant isolation.
   - Centralized authentication handled via SAP Cloud Identity Services and XSUAA.
