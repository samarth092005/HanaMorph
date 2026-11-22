# HANAMORPH — SAP BW OBJECT DISCOVERY COVERAGE
**Target SAP System:** SAP NetWeaver AS ABAP 7.53 / SAP BW 7.50 (`S21`)  
**Specification:** Complete Coverage Across 17 SAP BW & DDIC Object Types  

---

## 1. Object Type Discovery Coverage Matrix

The following table details the discovery strategy, extraction channel, and operational support status across all 17 object types:

| # | Object Type | Technical Code | Description | Discovery Strategy on NetWeaver 7.53 | Provenance | Status |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **DataStore Object (advanced)** | `ADSO` | Modern persistent staging & corporate memory layer | Runtime tables extracted via live ADT; Semantics via BWMT cache | `LIVE_VERIFIED` / `CACHED` | **SUPPORTED** |
| 2 | **CompositeProvider** | `HCPR` | Virtual union/join multi-provider layer | Ingested via BWMT XML cache (`.bw/` XML structure) | `CACHED` | **SUPPORTED** |
| 3 | **InfoObject** | `IOBJ` | Central business dimension / key figure | Ingested via BWMT XML cache & live DDIC check tables | `CACHED` / `LIVE_VERIFIED` | **SUPPORTED** |
| 4 | **InfoSource** | `ISFS` | Intermediate data pipeline transformation layer | Metadata parsed via BWMT cache & DDIC definitions | `CACHED` | **SUPPORTED** |
| 5 | **Transformation** | `TRFN` | Field mapping rules & routine definitions | Parsed via BWMT metadata XML cache | `CACHED` | **SUPPORTED** |
| 6 | **Data Transfer Process** | `DTP` | Data loading extraction & delta execution parameters | Extracted via BWMT XML & runtime job history tables | `CACHED` | **SUPPORTED** |
| 7 | **DataSource** | `RSDS` / `OSOA` | Source extraction interface & delta queues | Extracted via ADT DDIC extraction of extract structures | `LIVE_VERIFIED` | **SUPPORTED** |
| 8 | **BEx / BW Query** | `ELEM` / `REP` | Analytical reporting definition | Ingested via BWMT query designer XML cache | `CACHED` | **SUPPORTED** |
| 9 | **Classic DSO** | `ODSO` | Standard / Write-optimized classic DSO | Live ADT DDIC extraction of Active/New/ChangeLog tables | `LIVE_VERIFIED` | **SUPPORTED** |
| 10 | **InfoCube** | `CUBE` | Classic star-schema multidimensional cube | Live ADT DDIC extraction of F-table and E-table | `LIVE_VERIFIED` | **SUPPORTED** |
| 11 | **MultiProvider** | `MPRO` | Classic virtual union provider | Ingested via BWMT cache or classic repository export | `CACHED` | **SUPPORTED** |
| 12 | **InfoSet** | `ISET` | Classic relational join provider | Ingested via BWMT cache / classic repository export | `CACHED` | **SUPPORTED** |
| 13 | **Open ODS View** | `ODSV` | Virtual external table wrapper | Unsupported on NetWeaver 7.53 (Flagged as BLOCKED) | `N/A` | **DEPRECATED** |
| 14 | **Semantic Partitioned Object** | `SPO` | Partitioned classic DSO or Cube | Decomposed into underlying constituent ADSOs/DSOs | `CACHED` | **SUPPORTED** |
| 15 | **VirtualProvider** | `VPRO` | Direct BAPI / Function Module access provider | Flagged for manual refactoring to Datasphere Remote Table | `CACHED` | **MANUAL** |
| 16 | **DDIC Table** | `TABL` | Transparent database tables (`/BIC/*`, `DD02L`, etc.) | Extracted live via `/sap/bc/adt/ddic/tables/{name}` | `LIVE_VERIFIED` | **SUPPORTED** |
| 17 | **DDIC View** | `VIEW` | Database and maintenance views (`/BIC/AZSAM_*6`) | Extracted live via `/sap/bc/adt/vit/wb/object_type/viewdv` | `LIVE_VERIFIED` | **SUPPORTED** |

---

## 2. Extraction Detail for Key S21 Objects

### A. Sales Order DataStore (`ZSAM_SO01`)
- **Underlying Tables:**
  - Inbound Queue: `/BIC/AZSAM_SO011` (`TABL/DT`)
  - Active Data: `/BIC/AZSAM_SO012` (`TABL/DT`)
  - Change Log: `/BIC/AZSAM_SO013` (`TABL/DT`)
- **Reporting View:** `/BIC/AZSAM_SO017` (`VIEW/DV`)
- **Key Fields:** `ORDER_ID` (`CHAR` 10, Key)
- **Measures:** `AMOUNT` (`CURR` 15.2, Currency: `CURRENCY`)

### B. Purchase Requisition DataStore (`ZSAM_PR01`)
- **Underlying Tables:**
  - Inbound Queue: `/BIC/AZSAM_PR011` (`TABL/DT`) — Verified: 14 fields extracted live via ADT.
  - Active Data: `/BIC/AZSAM_PR012` (`TABL/DT`)
  - Change Log: `/BIC/AZSAM_PR013` (`TABL/DT`)
- **Extraction View:** `/BIC/AZSAM_PR016` (`VIEW/DV`)
- **Reporting View:** `/BIC/AZSAM_PR017` (`VIEW/DV`)
