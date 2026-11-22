# HANAMORPH BW Migration & Modernization Studio
# Target Modernization Strategies Architecture — Architecture Blueprint 1.0

**Document Reference:** `BW-MIG-TARG-1.0`  
**Status:** Approved for Architecture Design  
**Target Studio:** `BW_Migration_Studio/bw-studio`  
**Classification:** SAP Enterprise Modernization Architecture  

---

## 1. Overview of the Four Target Modernization Routes

Enterprise modernization cannot follow a "one-size-fits-all" path. Depending on legacy complexity, ABAP footprint, analytical consumption, and target cloud landscape, HANAMORPH provides four autonomous target generation routes:
1. **Route 1: Native SAP Datasphere Route** (Pure cloud semantic fabric and SQL data warehouse)
2. **Route 2: SAP BW Bridge Route** (ABAP-hosted BW modernization container on SAP BTP)
3. **Route 3: SAP Business Data Cloud (BDC) Route** (Packaged Data Products and Data Sharing Cockpit)
4. **Route 4: Hybrid Modernization Route** (Dual-run coexistence, Change Log CDC, staged cutover)

---

## 2. Route 1: Native SAP Datasphere Architecture

The Native Datasphere route generates pure Core Data Services CSN 2.0 artifacts, HANA Cloud SQL DDL, and Replication Flow definitions, completely eliminating legacy ABAP runtimes.

### Diagram 9: Native Datasphere Target Route

```mermaid
flowchart LR
    subgraph SOURCE_OBJECTS["Discovered BW Metadata"]
        SRC_ADSO["Standard ADSO\n(e.g., ZSAM_SO01)"]
        SRC_TRFN["Transformation Rules\n(Formulas & Currency Links)"]
        SRC_CP["CompositeProvider\n(Join Nodes & Mappings)"]
        SRC_QRY["BW BEx Query\n(Calculations & Variables)"]
    end

    subgraph HANAMORPH_DSP_GEN["Datasphere Generation Engine (datasphere.py)"]
        GEN_TABLE["Table Generator\n- Dynamic PK Detection\n- Semantic Amount/Currency"]
        GEN_FLOW["Replication Flow Builder\n- Delta CDC Mapping\n- Source/Target Endpoints"]
        GEN_VIEW["View Generator\n- SQL Join Nodes\n- Projection Mapping"]
        GEN_CUBE["Analytic Model Builder\n- @Analytics.dataCategory: CUBE\n- Measures & Dimensions"]
    end

    subgraph TARGET_DSP_ARTIFACTS["Generated Datasphere Artifacts"]
        OUT_CSN["CSN 2.0 Local Table\n(type: 'entity')"]
        OUT_FLOW["Replication Flow JSON\n(ZSAM_SO01.flow.json)"]
        OUT_VIEW["Graphical / SQL View\n(type: 'view')"]
        OUT_AM["Analytic Model\n(type: 'view', Cube)"]
        OUT_DDL["SAP HANA Cloud DDL\n(Column Tables & Views)"]
    end

    SRC_ADSO --> GEN_TABLE
    SRC_ADSO --> GEN_FLOW
    SRC_TRFN --> GEN_VIEW
    SRC_CP --> GEN_VIEW
    SRC_QRY --> GEN_CUBE

    GEN_TABLE --> OUT_CSN
    GEN_TABLE --> OUT_DDL
    GEN_FLOW --> OUT_FLOW
    GEN_VIEW --> OUT_VIEW
    GEN_CUBE --> OUT_AM
```

### 2.1 Artifact Specifications & Official SAP Documentation Anchors
- **CSN 2.0 Schema Definition:** Local Tables are emitted as `@EndUserText.label` annotated CDS entities with explicit semantic associations (`@Semantics.amount.currencyCode`).
- **SAP Reference:** [SAP Datasphere Modeling Documentation](https://help.sap.com/docs/SAP_DATASPHERE/c8a5410afbbf4928ac78477215c0e178/e6b22c8cb93845dc8a113ecaa68a62f5.html).
- **SAP HANA Cloud DDL:** High-performance Column Tables with `PRIMARY KEY` constraints and foreign key annotations matching the CSN entity.
- **Replication Flows (`.flow.json`):** Captures source connection names, source container paths, target space names, delta load type (`DeltaWithInitialLoad`), and Change Log CDC mappings.

---

## 3. Route 2: SAP BW Bridge Architecture

For workloads containing business-critical legacy ABAP routines (Start, End, or Field routines) that cannot be immediately rewritten into SQL, the **SAP BW Bridge** route provides a safe harbor on SAP BTP.

### Diagram 10: SAP BW Bridge Target Route

```mermaid
flowchart LR
    subgraph SOURCE_COMPLEX["Complex BW Objects"]
        SRC_ADSO_COMP["Complex ADSO\n(Active Table + Change Log)"]
        SRC_ROUTINE["ABAP Routines\n(Start / End / Expert)"]
        SRC_IOBJ["Custom InfoObjects\n(Navigational Attributes)"]
    end

    subgraph BRIDGE_GENERATOR["BW Bridge Generator (bridge.py)"]
        XML_PACK["abapGit Deserializer & Packager"]
        ABAP_WRAP["BTP ABAP Cloud Compatibility Checker\n- Replaces Obsolete BAPIs\n- Wraps Routine Logic"]
        DEST_MAP["BTP RFC Destination Allocator"]
    end

    subgraph BRIDGE_PACKAGE["Deployable BW Bridge Package"]
        OUT_ABAPGIT["abapGit Repository Folder\n- src/adso_zsam_so01.adso.xml\n- src/zcl_trfn_routine.clas.abap\n- src/iobj_zcust.iobj.xml"]
        OUT_BRIDGE_CSN["Datasphere Inbound CSN Bridge Entity\n(Remote Table Stub for Space)"]
        OUT_MANIFEST["Bridge Conversion Manifest JSON"]
    end

    SRC_ADSO_COMP --> XML_PACK
    SRC_ROUTINE --> ABAP_WRAP
    SRC_IOBJ --> XML_PACK

    XML_PACK --> OUT_ABAPGIT
    ABAP_WRAP --> OUT_ABAPGIT
    DEST_MAP --> OUT_BRIDGE_CSN
    DEST_MAP --> OUT_MANIFEST
```

### 3.1 Conversion Capabilities & Technical Prerequisites
- **Supported Objects:** Standard ADSOs with change log, InfoObjects, Transformations, and DTPs.
- **ABAP Language Version:** Generated routine wrappers are verified against **ABAP for Cloud Development** (Restricted ABAP syntax; zero direct OS or memory access).
- **SAP Reference:** [SAP BW Bridge Modeling Guide](https://help.sap.com/docs/SAP_BW_BRIDGE/0eec0d68141541d1b07893a39944924e/e6fd7e3e46e84d4da58df4c8a2455e92.html).

---

## 4. Route 3: SAP Business Data Cloud (BDC) Architecture

SAP Business Data Cloud (BDC) provides federated semantic sharing without forcing data movement through the **BW Data Product Generator** and **Data Sharing Cockpit**.

### Diagram 11: BDC Data Product Target Route

```mermaid
flowchart LR
    subgraph SOURCE_BW_SEMANTICS["BW Analytical Core"]
        INFOPROV["Governed InfoProvider\n(ADSO / CompositeProvider)"]
        BW_QUERY["Validated BW Query\n(Business Measures & Variables)"]
        AUTHORIZ["Analysis Authorizations\n(RSECADMIN Filters)"]
    end

    subgraph BDC_GENERATOR["BDC Engine (bdc.py)"]
        SUB_BUILDER["BW Data Subscription Configurator\n(Service: cl_rso_data_product)"]
        COCKPIT_MAP["Data Sharing Cockpit Contract Mapper"]
        MANIFEST_GEN["BDC Data Product Manifest Builder"]
    end

    subgraph BDC_TARGET["Packaged BDC Data Product"]
        DATA_PROD["Data Product Descriptor\n(data-product.json)\n- Product ID & Version\n- SLA & Freshness Metadata\n- Semantic Business Terms"]
        FILE_SPACE["BW File Space Definition\n(Remote Sharing Endpoint)"]
        AUTH_CONTRACT["Sharing Governance Contract\n(Entitlements & Allowed Consumers)"]
    end

    INFOPROV --> SUB_BUILDER
    BW_QUERY --> SUB_BUILDER
    AUTHORIZ --> COCKPIT_MAP

    SUB_BUILDER --> DATA_PROD
    SUB_BUILDER --> FILE_SPACE
    COCKPIT_MAP --> AUTH_CONTRACT
```

### 4.1 Technical Specifications & Official SAP Citations
- **Integration Class:** Employs the official SAP BW/4HANA Data Product generation interface: `CL_RSO_DATA_PRODUCT`.
- **Consumer Protocol:** Exposed over OData v4 and SAP Datasphere Data Sharing Cockpit contracts.
- **SAP Reference:** [SAP BW/4HANA Data Product Integration](https://help.sap.com/docs/SAP_BW4HANA/ed919380760a44388ab90e6bb3e7480a).

---

## 5. Route 4: Hybrid Modernization Architecture

Enterprise migrations span months of coexistence. The Hybrid route orchestrates dual-run replication, Change Log CDC streams, and phased cutovers.

### Diagram 12: Hybrid Target Route

```mermaid
flowchart LR
    subgraph SAP_BW_PROD["Legacy SAP BW (Source System S21)"]
        BW_INBOUND["Operational Inbound (DTPs)"]
        BW_ADSO["Standard ADSO (ZSAM_SO01)"]
        BW_CLOG["Change Log Table (/BIC/AZSAM_SO012)"]
    end

    subgraph REPLICATION_FABRIC["Dual-Run Replication Bridge"]
        REP_FLOW["SAP Datasphere Replication Flow\n(Real-Time CDC Stream)"]
        FLOW_MONITOR["Lag & Checksum Monitor\n(Tracks Source & Target Record Counts)"]
    end

    subgraph DATASPHERE_TARGET["Target SAP Datasphere Space"]
        DSP_TABLE["Local Table (ZSAM_SO01_T)"]
        DSP_VIEW["Analytical Consumption View"]
    end

    subgraph CONSUMERS["Reporting Consumers"]
        SAC_REPORT["SAP Analytics Cloud Dashboards"]
    end

    BW_INBOUND --> BW_ADSO
    BW_ADSO --> BW_CLOG
    BW_CLOG -->|CDC Stream| REP_FLOW
    REP_FLOW --> DSP_TABLE
    DSP_TABLE --> DSP_VIEW
    
    REP_FLOW -.->|Status & Counts| FLOW_MONITOR
    
    BW_ADSO -->|Legacy Reporting| SAC_REPORT
    DSP_VIEW -.->|Parallel Shadow Report| SAC_REPORT
```

---

## 6. External Data Movement & Orchestration

> [!IMPORTANT]
> **Strict Operational Boundary:** HANAMORPH never acts as the bulk data mover. It defines the flow specifications and monitors execution state via native SAP APIs.

### Diagram 13: External Data Movement & Orchestration Pipeline

```mermaid
flowchart TD
    subgraph HANAMORPH_SPEC["1. Specification Generation (HANAMORPH)"]
        GEN_SPEC["Generate Replication Flow Specification\n(ZSAM_SO01.flow.json)"]
        GEN_SPEC --> VAL_SYNTAX["Validate Schema & Endpoints (Level 1–5 Validation)"]
    end

    subgraph HITL_APPROVAL["2. Human-in-the-Loop Governance Gate"]
        VAL_SYNTAX --> GATE_APPROVE{"Migration Architect\nSigns Off Approval Gate?"}
        GATE_APPROVE -- No --> REVISE["Return to Configuration"]
        GATE_APPROVE -- Yes --> SIGNED_FLOW["Cryptographically Signed Flow Bundle"]
    end

    subgraph EXTERNAL_EXECUTION["3. Native SAP Execution Fabric (Out-of-Process)"]
        SIGNED_FLOW --> DEPLOY_DSP["Deploy via Datasphere CLI / API\n(datasphere objects import)"]
        DEPLOY_DSP --> START_FLOW["Execute Replication Flow in Datasphere\n(Initial Load + Continuous CDC)"]
        START_FLOW --> DP_AGENT["SAP Data Provisioning Agent\nStreams Data Directly from BW to HANA Cloud"]
    end

    subgraph STATUS_MONITORING["4. Evidence Collection & Reconciliation (HANAMORPH)"]
        DP_AGENT --> FLOW_STATUS["Poll Execution Status API\n(/api/v1/datasphere/tasks/*)"]
        FLOW_STATUS --> HARVEST_EVAL["Collect Reconciliation Evidence\n- Record Count Source vs Target\n- Currency Hash Checksums"]
        HARVEST_EVAL --> AUDIT_RECORD[("Audit & Evidence DB\n(Proof Level 7 Complete)")]
    end
```
