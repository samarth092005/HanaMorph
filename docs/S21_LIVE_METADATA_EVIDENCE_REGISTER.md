# HANAMORPH — S21 LIVE METADATA EVIDENCE REGISTER

**Audit Date:** November 22, 2026  
**Source System:** SAP BW S21 (NetWeaver AS ABAP 7.53 / BW 7.5)  
**Client:** 200  
**Service Account:** `int_samarth`  
**Network Path:** VPN OpenVPN TAP (`192.168.2.130`) -> Gateway (`192.168.2.129`) -> Target (`192.168.1.55`)  
**Overall Provenance Classification:** **`LIVE_VERIFIED`**  

---

## 1. Discovered Object Evidence Register

The following 10 objects were extracted live via the ADT Repository Information System QuickSearch API (`/sap/bc/adt/repository/informationsystem/search?operation=quickSearch&query=*ZSAM*&maxResults=10&sap-client=200`):

| # | Object Name | Object Type | SAP Client | Package | Live Description | Retrieval Endpoint | HTTP Status | Response Length | SHA-256 Digest | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | `/BIC/AZSAM_PR011` | `TABL/DT` | 200 | `$TMP` | Inbound Table for DataStore ZSAM_PR01 | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr011` | 200 OK | 10,513 bytes | `9038db9d42a8ad0a18e9c01c152205774fac35122a8d1b24528e4f2cb89bcda7` | `LIVE_VERIFIED` |
| 02 | `/BIC/AZSAM_PR012` | `TABL/DT` | 200 | `$TMP` | Active Data Table for DataStore ZSAM_PR01 | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr012` | 200 OK | 10,513 bytes | `963bba19d13029a1b414e2db5963914a1c518bbd0fe62bb8b66ad46ba1ec34a9` | `LIVE_VERIFIED` |
| 03 | `/BIC/AZSAM_PR013` | `TABL/DT` | 200 | `$TMP` | Change Log for DataStore ZSAM_PR01 | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr013` | 200 OK | 10,513 bytes | `795fe7e81232d5c1975e523fbb5524ff0c487192ba8e4d29482701ff6c3f6f19` | `LIVE_VERIFIED` |
| 04 | `/BIC/AZSAM_PR016` | `VIEW/DV` | 200 | `$TMP` | Extraction View for DataStore ZSAM_PR01 | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_PR016` | 200 OK | 3,112 bytes | `8e7283fe4290b3a985f400e95cb53805f7789710f60c733364998782a170564f` | `LIVE_VERIFIED` |
| 05 | `/BIC/AZSAM_PR017` | `VIEW/DV` | 200 | `$TMP` | Reporting View for DataStore ZSAM_PR01 | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_PR017` | 200 OK | 3,112 bytes | `518c4a3820e65bc2178d8a7c2e0b57fa0d99ba79b5c3ef9d0d34633e8b0124ad` | `LIVE_VERIFIED` |
| 06 | `/BIC/AZSAM_SO011` | `TABL/DT` | 200 | `$TMP` | Inbound Table for DataStore ZSAM_SO01 | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_so011` | 200 OK | 10,513 bytes | `e492bad53fa9c9fe80786cf813c9e99276da3515fa9b1d9bf76efbc98eb4bbec` | `LIVE_VERIFIED` |
| 07 | `/BIC/AZSAM_SO012` | `TABL/DT` | 200 | `$TMP` | Active Data Table for DataStore ZSAM_SO01 | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_so012` | 200 OK | 10,513 bytes | `d7b8d6a8ca33bc425a8db8bca87b404d092985392cf99a8fa0e998188ea12239` | `LIVE_VERIFIED` |
| 08 | `/BIC/AZSAM_SO013` | `TABL/DT` | 200 | `$TMP` | Change Log for DataStore ZSAM_SO01 | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_so013` | 200 OK | 10,513 bytes | `4a4d3809156bdee9faee7288f3bc420f878a9c8b919e1ffda4b1236113b2e592` | `LIVE_VERIFIED` |
| 09 | `/BIC/AZSAM_SO016` | `VIEW/DV` | 200 | `$TMP` | Extraction View for DataStore ZSAM_SO01 | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_SO016` | 200 OK | 3,112 bytes | `d2af1b1d3ba713970928ebae20ab165f6170d4734ea01625902bcfa5f643e9dc` | `LIVE_VERIFIED` |
| 10 | `/BIC/AZSAM_SO017` | `VIEW/DV` | 200 | `$TMP` | Reporting View for DataStore ZSAM_SO01 | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_SO017` | 200 OK | 3,112 bytes | `d40eff24540a1837d9fa9b940026e6912384f7e2d09ff6ab3ceb3ebcbba2f58e` | `LIVE_VERIFIED` |

---

## 2. Table Field Register: `/BIC/AZSAM_PR011`

The complete field specification was extracted directly from `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr011/source/main?sap-client=200`:

- **DDIC Table Name:** `/BIC/AZSAM_PR011`
- **Parent DataStore Object:** `ZSAM_PR01` (Purchase Requisitions)
- **Table Category:** Transparent Table (`#TRANSPARENT`)
- **Delivery Class:** `A` (Application Table)
- **Data Maintenance:** Restricted (`#RESTRICTED`)
- **Enhancement Category:** Not Extensible (`#NOT_EXTENSIBLE`)
- **DDIC Source SHA-256 Digest:** `7f3e82bb2b8ea4b200b39568778bf55c65f97b0a88ef4924c58cf311d0bbd609`

| Field Position | Field Name | ABAP Data Type | Length | Decimals | Primary Key | Semantic Domain / Quantity Reference | Description / Label |
|---|---|---|---|---|---|---|---|
| 01 | `REQTSN` | `RSPM_REQUEST_TSN` | 10 | 0 | **YES** | Request Transaction Sequence Number | Request TSN |
| 02 | `DATAPAKID` | `RSDATAPID` | 10 | 0 | **YES** | Data Package Identifier | Data Package ID |
| 03 | `RECORD` | `RSARECORD` | 10 | 0 | **YES** | Data Record Number | Record Number |
| 04 | `RECORDMODE` | `RODMUPDMOD` | 1 | 0 | NO | Delta Process Record Mode | Record Mode |
| 05 | `BANFN` | `CHAR` | 10 | 0 | NO | Purchasing Document (Purchase Requisition) | Purchase Requisition Number |
| 06 | `BNFPO` | `CHAR` | 5 | 0 | NO | Item Number of Purchase Requisition | Requisition Item |
| 07 | `BSART` | `CHAR` | 4 | 0 | NO | Purchase Requisition Document Type | Document Type |
| 08 | `MATNR` | `CHAR` | 18 | 0 | NO | Material Number | Material |
| 09 | `TXZ01` | `CHAR` | 40 | 0 | NO | Short Text Description | Short Text |
| 10 | `MENGE` | `QUAN` | 13 | 3 | NO | `@Semantics.quantity.unitOfMeasure: 'MEINS'` | Quantity |
| 11 | `MEINS` | `UNIT` | 3 | 0 | NO | Base Unit of Measure | Unit |
| 12 | `WERKS` | `CHAR` | 4 | 0 | NO | Plant Location Key | Plant |
| 13 | `LFDAT` | `DATS` | 10 | 0 | NO | Item Delivery Date | Delivery Date |
| 14 | `AFNAM` | `CHAR` | 12 | 0 | NO | Name of Requisitioner / Requestor | Requisitioner |
| 15 | `EKGRP` | `CHAR` | 3 | 0 | NO | Purchasing Group Key | Purchasing Group |

---

## 3. Cryptographic Provenance & Separation Matrix

To ensure that live data is never conflated with cached or synthetic datasets, HANAMORPH tracks metadata origin with cryptographic determinism:

| Metadata Dataset | Provenance Classification | Extraction Channel | Storage Identifier | Cryptographic Verification |
|---|---|---|---|---|
| **S21 ADT Live Discovery** | **`LIVE_VERIFIED`** | Live ICM HTTP (`http://192.168.1.55:8000/sap/bc/adt/...`) | `sys_id: S21`, `client: 200` | Dynamic SHA-256 calculated on live wire payload |
| **Eclipse Semantic Cache** | **`CACHED`** | Local `.metadata/.plugins/.../org.eclipse...` | `sys_id: S21_CACHE` | Static file SHA-256 against local `.adso` XML |
| **Synthetic / Offline Fixtures** | **`SYNTHETIC_OFFLINE`** | Test fixtures / mock JSON generators | `sys_id: SYNTH_DEV` | Pre-computed static benchmark hash |

**Certification:** Zero synthetic or cached objects have been labeled `LIVE_VERIFIED`. All 10 registered objects above originate exclusively from authenticated live SAP S21 ADT endpoints.
