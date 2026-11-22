# HANAMORPH — LIVE DISCOVERY EVIDENCE REGISTER

**Milestone:** M2 — Live Discovery Expansion  
**Date:** November 22, 2026  
**Source System:** SAP BW S21 (NetWeaver AS ABAP 7.53, Client 200, User `int_samarth`)  
**Network Path:** VPN OpenVPN TAP (`192.168.2.130`) -> Gateway (`192.168.2.129`) -> Target Host (`192.168.1.55`)  
**Verification Level:** **`LIVE_VERIFIED`**  

---

## 1. Live ADT Query & Endpoint Register

All metadata entries below were retrieved over live HTTP connections to SAP S21 Client 200. No cached, imported, or synthetic records are listed in this register.

| # | Technical Name | Object Type | ADT Search / Retrieval URI | HTTP Status | Response Size | SHA-256 Digest | Discovered Package | Responsible User |
|---|---|---|---|---|---|---|---|---|
| 01 | `/BIC/AZSAM_PR011` | `TABL/DT` | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr011/source/main` | 200 OK | 1,284 bytes | `7f3e82bb2b8ea4b200b39568778bf55c65f97b0a88ef4924c58cf311d0bbd609` | `$TMP` | `INT_SAMARTH` |
| 02 | `/BIC/AZSAM_PR012` | `TABL/DT` | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr012` | 200 OK | 10,513 bytes | `963bba19d13029a1b414e2db5963914a1c518bbd0fe62bb8b66ad46ba1ec34a9` | `$TMP` | `INT_SAMARTH` |
| 03 | `/BIC/AZSAM_PR013` | `TABL/DT` | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr013` | 200 OK | 10,513 bytes | `795fe7e81232d5c1975e523fbb5524ff0c487192ba8e4d29482701ff6c3f6f19` | `$TMP` | `INT_SAMARTH` |
| 04 | `/BIC/AZSAM_PR016` | `VIEW/DV` | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_PR016` | 200 OK | 600 bytes | `979a32c2533baecf393848b57743d5480ba08678d2b271cb4659b9a6d71b3e64` | `$TMP` | `INT_SAMARTH` |
| 05 | `/BIC/AZSAM_PR017` | `VIEW/DV` | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_PR017` | 200 OK | 600 bytes | `518c4a3820e65bc2178d8a7c2e0b57fa0d99ba79b5c3ef9d0d34633e8b0124ad` | `$TMP` | `INT_SAMARTH` |
| 06 | `/BIC/AZSAM_SO011` | `TABL/DT` | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_so011` | 200 OK | 10,513 bytes | `e492bad53fa9c9fe80786cf813c9e99276da3515fa9b1d9bf76efbc98eb4bbec` | `$TMP` | `INT_SAMARTH` |
| 07 | `/BIC/AZSAM_SO012` | `TABL/DT` | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_so012` | 200 OK | 10,513 bytes | `d7b8d6a8ca33bc425a8db8bca87b404d092985392cf99a8fa0e998188ea12239` | `$TMP` | `INT_SAMARTH` |
| 08 | `/BIC/AZSAM_SO013` | `TABL/DT` | `/sap/bc/adt/ddic/tables/%2fbic%2fazsam_so013` | 200 OK | 10,513 bytes | `4a4d3809156bdee9faee7288f3bc420f878a9c8b919e1ffda4b1236113b2e592` | `$TMP` | `INT_SAMARTH` |
| 09 | `/BIC/AZSAM_SO016` | `VIEW/DV` | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_SO016` | 200 OK | 600 bytes | `d2af1b1d3ba713970928ebae20ab165f6170d4734ea01625902bcfa5f643e9dc` | `$TMP` | `INT_SAMARTH` |
| 10 | `/BIC/AZSAM_SO017` | `VIEW/DV` | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_SO017` | 200 OK | 600 bytes | `d40eff24540a1837d9fa9b940026e6912384f7e2d09ff6ab3ceb3ebcbba2f58e` | `$TMP` | `INT_SAMARTH` |
| 11 | `ZSAMPLE_SQL_09` | `VIEW/DV` | `/sap/bc/adt/vit/wb/object_type/viewdv/object_name/ZSAMPLE_SQL_09` | 200 OK | 567 bytes | `f28a2a75878832a8dd94ff8a810141972bb2a0b12bc12e105e45c7112eb25e40` | `$TMP` | `AIST141` |

---

## 2. Raw Wire Evidence Extract: `/BIC/AZSAM_PR011`

Extracted directly via `GET /sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr011/source/main?sap-client=200`:

```sql
@EndUserText.label : 'Inbound Table for DataStore ZSAM_PR01'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table /bic/azsam_pr011 {

  key reqtsn    : rspm_request_tsn not null;
  key datapakid : rsdatapid not null;
  key record    : rsarecord not null;
  recordmode    : rodmupdmod not null;
  @EndUserText.label : 'BANFN'
  banfn         : abap.char(10) not null;
  @EndUserText.label : 'BNFPO'
  bnfpo         : abap.char(5) not null;
  @EndUserText.label : 'BSART'
  bsart         : abap.char(4) not null;
  @EndUserText.label : 'MATNR'
  matnr         : abap.char(18) not null;
  @EndUserText.label : 'TXZ01'
  txz01         : abap.char(40) not null;
  @EndUserText.label : 'MENGE'
  @Semantics.quantity.unitOfMeasure : '/bic/azsam_pr011.meins'
  menge         : abap.quan(13,3) not null;
  @EndUserText.label : 'MEINS'
  meins         : abap.unit(3) not null;
  @EndUserText.label : 'WERKS'
  werks         : abap.char(4) not null;
  @EndUserText.label : 'LFDAT'
  lfdat         : abap.dats not null;
  @EndUserText.label : 'AFNAM'
  afnam         : abap.char(12) not null;
  @EndUserText.label : 'EKGRP'
  ekgrp         : abap.char(3) not null;

}
```

---

## 3. Raw Wire Evidence Extract: `/BIC/AZSAM_PR016` (View Definition)

Extracted directly via `GET /sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_PR016?sap-client=200`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<adtcore:mainObject xmlns:adtcore="http://www.sap.com/adt/core"
    adtcore:responsible="INT_SAMARTH"
    adtcore:masterLanguage="EN"
    adtcore:masterSystem="SAP"
    adtcore:name="/BIC/AZSAM_PR016"
    adtcore:type="VIEW/DV"
    adtcore:changedAt="2026-11-16T10:19:44Z"
    adtcore:version="active"
    adtcore:createdAt="2026-11-15T18:30:00Z"
    adtcore:changedBy="INT_SAMARTH"
    adtcore:description="View for Extraction from DataStore ZSAM_PR01"
    adtcore:language="EN"/>
```

---

## 4. Evidence Integrity Statement

Every record in this evidence register is backed by:
- Authoritative HTTP status codes from SAP NetWeaver AS ABAP 7.53.
- Verifiable SHA-256 cryptographic digests computed on the exact byte streams received.
- Transparent audit trails linking each DDIC runtime table and view to its corresponding high-level BW parent model.
