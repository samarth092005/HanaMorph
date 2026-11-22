# HANAMORPH — SAP BW OBJECT SUPPORT MATRIX

**Milestone:** M2 — Live Discovery Expansion  
**Date:** November 22, 2026  
**System Target:** SAP NetWeaver AS ABAP 7.53 / BW 7.5 (Client 200)  
**Target Environments:** SAP Datasphere, SAP BW Bridge, SAP Business Data Cloud (BDC), Hybrid  

---

## 1. Full 17-Category SAP BW Object Support Matrix

This matrix establishes the definitive support, extraction mechanism, required authorizations, and target migration routes for all 17 SAP BW object types under the HANAMORPH modernization framework.

| # | Object Type | Technical ID | Description | Live SAP Interface / Endpoint | Required Authorization | Implementation Status | Verification Level | Supported Target Routes |
|---|---|---|---|---|---|---|---|---|
| 01 | **Advanced DataStore Object** | `ADSO` | Modern BW/4HANA & BW 7.5 persistence layer with inbound, active, and changelog tables. | `/sap/bc/adt/ddic/tables/%2fbic%2fa.../source/main` & `.bw/adso` | `S_TABU_DIS (03)`, `S_DEVELOP (03)`, `S_RS_ADSO (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** | Native Datasphere (Local Table), BW Bridge, BDC, Hybrid |
| 02 | **Classic DataStore Object** | `ODSO` | Legacy BW 7.x relational persistence with active data, new data, and changelog tables. | `/sap/bc/adt/ddic/tables/%2fbic%2fa...` & DDIC catalog | `S_TABU_DIS (03)`, `S_DEVELOP (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** | Native Datasphere (Local Table), BW Bridge, BDC |
| 03 | **InfoCube** | `CUBE` | Multidimensional star/snowflake schema with Fact (`/BIC/F*`, `/BIC/E*`) and Dimension (`/BIC/D*`) tables. | `/sap/bc/adt/ddic/tables/` Fact & Dim table definitions | `S_TABU_DIS (03)`, `S_DEVELOP (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** | Native Datasphere (Analytic Model), BW Bridge |
| 04 | **CompositeProvider** | `HCPR` | Modern semantic layer combining multiple providers via Join and Union operations. | `/sap/bc/adt/vit/wb/object_type/viewdv/...` & `.bw/hcpr` | `S_RS_COMP (03)`, `S_DEVELOP (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** & **CACHED** | Native Datasphere (Graphical View / Analytic Model), BDC |
| 05 | **MultiProvider** | `MPRO` | Legacy semantic Union provider combining InfoCubes and DSOs. | Offline XML model / Metadata transport bundle | `S_RS_COMP (03)` | **IMPLEMENTED** | **CACHED / IMPORTED** | Native Datasphere (Graphical View), BW Bridge |
| 06 | **InfoObject (Characteristic)** | `IOBJ_CHA` | Master data dimension with text (`/BIC/T*`), attribute (`/BIC/P*`), and hierarchy tables. | `/sap/bc/adt/ddic/tables/` master data table DDL | `S_TABU_DIS (03)`, `S_RS_IOBJ (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** | Native Datasphere (Dimension View), BW Bridge, BDC |
| 07 | **InfoObject (Key Figure)** | `IOBJ_KYF` | Quantitative measure with data types, units, and currency references. | Extracted from ADSO/HCPR table field definitions | `S_RS_IOBJ (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** | Native Datasphere (Measure / Currency Ref) |
| 08 | **Transformation** | `TRFN` | Data mapping, field rules, currency conversions, and procedural ABAP routines. | `.bw/trcs` semantic cache & ADSO extraction rules | `S_RS_TRFN (03)` | **IMPLEMENTED** | **CACHED / IMPORTED** | Native Datasphere (Data Flow / SQL), BW Bridge (ABAP) |
| 09 | **Data Transfer Process** | `DTPA` | Data staging execution mechanism defining delta/full extraction and packet sizing. | Eclipse metadata & ADSO delta definitions | `S_RS_DTP (03)` | **IMPLEMENTED** | **CACHED / IMPORTED** | Datasphere Replication Flow / Transformation Flow |
| 10 | **DataSource** | `RSDS` | Source-system data extraction structure (SAPI, ODP, Flat File). | Extraction structure DDL via DDIC table inspection | `S_TABU_DIS (03)`, `S_RS_DS (03)` | **IMPLEMENTED** | **LIVE_VERIFIED / CACHED** | Datasphere Connection (ODP_BW / DP Agent) |
| 11 | **InfoPackage** | `ISIP` | Legacy 3.x scheduler for loading PSA tables. | Eclipse / Transport metadata bundle | `S_RS_ISIP (03)` | **IMPLEMENTED** | **CACHED / IMPORTED** | Datasphere Replication Flow |
| 12 | **Process Chain** | `RSPC` | Complex orchestration workflow scheduling data loading, activation, and index builds. | Orchestration lineage graphs in canonical dependencies | `S_RS_PC (03)` | **IMPLEMENTED** | **CACHED / IMPORTED** | Datasphere Task Chain / Airflow DAG |
| 13 | **BEx / BW Query** | `ELEM` | Reporting consumption definition with formulas, restricted key figures, and variables. | Generated Reporting Views (`VIEW/DV`) & `.bw/query` | `S_RS_COMP (03)` | **IMPLEMENTED** | **CACHED / IMPORTED** | Native Datasphere (Analytic Model), SAC Direct |
| 14 | **Open ODS View** | `ODSV` | Virtual layer exposing external tables or views without replication. | Probed live (Returns HTTP 400 on S21 7.53) | N/A | **UNSUPPORTED ON S21** | **VERIFIED UNSUPPORTED** | Native Datasphere (View over Remote Table) |
| 15 | **HANA Calculation View** | `VIEW` | Native SAP HANA SQL calculation view in SAP NetWeaver underlying database. | `/sap/bc/adt/vit/wb/object_type/viewdv/...` | `S_DEVELOP (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** | Native Datasphere (SQL View / Remote HANA) |
| 16 | **BW Extractor** | `ROOSOURCE` | SAP standard ERP extraction catalog (e.g. 2LIS_02_ITM, 0FI_GL_14). | SAPI catalog definitions in canonical model | `S_TABU_DIS (03)` | **IMPLEMENTED** | **CACHED / IMPORTED** | Datasphere Replication Flow |
| 17 | **Source System Reference** | `RSLOGSYS` | Logical system definition connecting S/4HANA, ERP, or external systems. | Configured source system mappings in `ConnectionHub` | `S_TABU_DIS (03)` | **IMPLEMENTED** | **LIVE_VERIFIED** | Datasphere Connection Space Pairing |

---

## 2. Target Route Feasibility & Rule Mapping

For each supported object type, HANAMORPH maps the object to the most effective target architecture based on objective scoring criteria:

1. **Native Datasphere:**
   - *Target Constructs:* Local Tables, Graphical Views, SQL Views, Analytic Models, Replication Flows.
   - *Best Suited For:* Standard ADSOs without procedural ABAP, CompositeProviders, Master Data InfoObjects, and Reporting Queries.
   - *Transformation:* 100% automated CSN 2.0 schema generation and HANA Cloud SQL DDL push-down.

2. **SAP BW Bridge:**
   - *Target Constructs:* Cloud-hosted ADSOs, CompositeProviders, InfoObjects, and ABAP-managed Data Transfer Processes.
   - *Best Suited For:* Objects with complex custom procedural ABAP routines (`ZSAM_FI*`), existing SAPI extractors, or deep legacy transformations requiring runtime preservation.

3. **Business Data Cloud (BDC) Data Products:**
   - *Target Constructs:* Governed Data Products, Open Data Fabric consumption contracts.
   - *Best Suited For:* Enterprise cross-domain consumption models with curated data contracts and SLA guarantees.

4. **Hybrid Modernization Route:**
   - *Target Constructs:* Staged extraction into BW Bridge with semantic consumption pushed to Native Datasphere Analytic Models.
   - *Best Suited For:* Complex landscapes balancing custom ABAP extraction with modern cloud self-service analytics.
