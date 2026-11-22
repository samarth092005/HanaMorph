# HANAMORPH BW Migration & Modernization Studio
# SAP Capability Verification Matrix — Architecture Blueprint 1.0 Review

**Document Reference:** `BW-MIG-CAP-2.0`  
**Status:** Completed Capability Audit  
**Classification:** SAP Enterprise Modernization Capability Verification  
**Evaluation Date:** November 21, 2026  

---

## 1. Classification Taxonomy

Every technical capability proposed in HANAMORPH Architecture Blueprint 1.0 is audited and assigned an evidence-backed status:
- **`VERIFIED`**: Proven through official SAP documentation and live system verification.
- **`VERIFIED_WITH_PREREQUISITES`**: Supported by SAP, but strictly contingent on specific releases, license scopes, or system configurations.
- **`PARTIALLY_VERIFIED`**: Supported in limited scenarios, but missing key metadata or documentation.
- **`UNVERIFIED`**: Proposed by HANAMORPH, but lacks authoritative SAP documentation proof.
- **`NOT_SUPPORTED`**: Explicitly contrary to official SAP architecture or prohibited by SAP platform rules.
- **`BLOCKED`**: Cannot be verified or executed due to missing credentials, firewall isolation, or unreleased platform software.

---

## 2. Source Connectivity & Metadata Extraction Matrix

| Interface / Component | Target Releases | Official SAP Reference URL | Verification Status | Architectural Evidence & Limitations |
| :--- | :--- | :--- | :---: | :--- |
| **ADT Discovery Endpoint** (`/sap/bc/adt/discovery`) | BW 7.5, BW/4HANA, S21 | [SAP Help: ADT REST Services](https://help.sap.com/docs/ABAP_PLATFORM_NEW/683d53ba421143179700697811395297/4ec9ef056e391014adc9fffe4e204223.html) | **`VERIFIED`** | Standard HTTP GET entrypoint. Returns XML service catalog and workspace collections. Proven live on S21. |
| **ADT BW Modeling Services** (`/sap/bc/adt/bw/modeling/*`) | BW 7.5 SP08+, BW/4HANA | [SAP Help: BW Modeling Tools](https://help.sap.com/docs/SAP_BW4HANA/107a6e8a38b7414db5cda37eedb0f80f/b4f91244e0074f4b9812674e2a8be9a9.html) | **`VERIFIED_WITH_PREREQUISITES`** | Requires active ICF node `/sap/bc/adt` and authorization object `S_ADT_RES` (`ACTVT=03`). Provides XML definitions for ADSOs, CompositeProviders, and Transformations. |
| **RFC Diagnostic Handshake** (`STFC_CONNECTION`, `RFC_PING`) | All SAP NW Releases | [SAP Note 321743 - RFC Ping and Connection Test](https://me.sap.com/notes/321743) | **`VERIFIED`** | Standard, benign diagnostic RFCs. Proven live on S21 TCP port 3300. |
| **RFC Table Read** (`RFC_READ_TABLE`) | BW 7.5, S21 | [SAP Note 382318 - RFC_READ_TABLE limitations](https://me.sap.com/notes/382318) | **`RESTRICTED / NOT_SUPPORTED`** | **Severe Limitations:** 512-byte row limit, fails on float/string/raw types, zero semantic awareness. Widely disabled by enterprise Basis/Security teams due to arbitrary table exposure risks. |
| **User Profile RFC** (`BAPI_USER_GET_DETAIL`) | All Releases | [SAP Note 1039860 - BAPI_USER_GET_DETAIL](https://me.sap.com/notes/1039860) | **`NOT_SUPPORTED (By Design)`** | Unjustified security risk for metadata tool. Requires `S_USER_GRP`. Excluded from HANAMORPH whitelist. |
| **Internal DTP Function** (`RS_DTP_GET_DETAIL`) | BW 7.5 | N/A (Internal SAP NetWeaver Function) | **`PARTIALLY_VERIFIED`** | Unreleased private function module. Works on S21 for read-only inspection, but signature changes across NetWeaver support packages. |
| **SES Search Catalog** (`RSOSM_CATALOG`) | BW 7.5 | [SAP Help: Search in BW](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483665dc35f83bb9e10000000a42189d.html) | **`UNVERIFIED / HIGH RISK`** | Often empty or unindexed if TREX/Embedded Search is inactive. Cannot serve as reliable catalog foundation. |
| **Standard DDIC Catalog Views** (`RSOOBJECTS`, `RSADSO`, `RSOCP`) | BW 7.5, BW/4HANA | [SAP Help: BW Metadata Repository](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED`** | Official SAP Data Dictionary repository tables. Fully populated in all BW systems. Reliable foundation for Level 1 catalog sweeps. |

---

## 3. SAP Datasphere Target Capabilities Matrix

| Target Capability | Official SAP Interface | Official SAP Reference URL | Verification Status | Architectural Reality & Constraints |
| :--- | :--- | :--- | :---: | :--- |
| **Core Schema Notation (CSN 2.0)** | Local Table / View JSON (`type: "entity"`, `type: "view"`) | [SAP Help: CSN in Datasphere](https://help.sap.com/docs/SAP_DATASPHERE/c8a5410afbbf4928ac78477215c0e178/e6b22c8cb93845dc8a113ecaa68a62f5.html) | **`VERIFIED`** | Fully supported. Standard CSN schema notation supported by `@sap/cds` and Datasphere import tools. |
| **HANA Cloud Column Tables DDL** | SQL DDL (`CREATE COLUMN TABLE`) | [SAP Help: SAP HANA Cloud SQL](https://help.sap.com/docs/HANA_CLOUD/4cd2e2e4b4234b1790e3615437a94f6c/20a6723275191014902187eb190b2b5a.html) | **`VERIFIED`** | Native SAP HANA Cloud SQL syntax supported in HDI containers and Datasphere open SQL schemas. |
| **Analytic Model Generation** | CSN View with `@Analytics.dataCategory: "CUBE"` | [SAP Help: Creating Analytic Models](https://help.sap.com/docs/SAP_DATASPHERE/c8a5410afbbf4928ac78477215c0e178/143588efebda4ca0b42f61ee5582f6f4.html) | **`VERIFIED_WITH_PREREQUISITES`** | Requires underlying dimension views and explicit semantic measures (`@Semantics.amount.currencyCode`). |
| **Replication Flows (.flow.json)** | Datasphere CLI / Import API | [SAP Help: Replication Flows in Datasphere](https://help.sap.com/docs/SAP_DATASPHERE/c8a5410afbbf4928ac78477215c0e178/48fb6a52865d4fa397240c9535f2fcb6.html) | **`VERIFIED_WITH_PREREQUISITES`** | Requires source ODP connectivity and Cloud Connector. Supports `DeltaWithInitialLoad`. |
| **Datasphere CLI Tooling** | `@sap/datasphere-cli` | [npm: @sap/datasphere-cli](https://www.npmjs.com/package/@sap/datasphere-cli) | **`VERIFIED`** | Official CLI tool. Supports `datasphere objects import`, `validate`, and `status`. |
| **Task Monitoring API** (`/api/v1/datasphere/tasks/*`) | N/A (Invented by Blueprint 1.0) | None | **`NOT_SUPPORTED`** | **INVENTED API:** Does not exist in SAP Datasphere documentation. External monitoring must use `@sap/datasphere-cli` or BTP logging. |

---

## 4. SAP BW Bridge Conversion Capabilities Matrix

| Capability | Official SAP Interface | Official SAP Reference URL | Verification Status | Architectural Reality & Constraints |
| :--- | :--- | :--- | :---: | :--- |
| **Shell Conversion** | SAP BW/4HANA Transfer Cockpit (`RSB4H`) | [SAP Help: Shell Conversion to BW Bridge](https://help.sap.com/docs/SAP_BW_BRIDGE/0eec0d68141541d1b07893a39944924e/e6fd7e3e46e84d4da58df4c8a2455e92.html) | **`VERIFIED`** | Official SAP conversion path. Transfers metadata shells from BW 7.5 to BW Bridge without data. |
| **Remote Conversion** | Transfer Cockpit (`RSB4H`) + RFC Transfer | [SAP Help: Remote Conversion Guide](https://help.sap.com/docs/SAP_BW_BRIDGE/0eec0d68141541d1b07893a39944924e/44f5c2f3844f434fb208b5f36e4f165a.html) | **`VERIFIED_WITH_PREREQUISITES`** | Requires BW 7.5 on HANA, dedicated RFC connection via Cloud Connector, and DMIS add-on. |
| **abapGit for Metadata Conversion** | abapGit XML Import of ADSOs | None | **`NOT_SUPPORTED`** | **CRITICAL FALLACY:** SAP BW Bridge does not support converting BW models via loose abapGit XML files. |
| **abapGit for Custom Code Sync** | BTP ABAP Environment Git Integration | [SAP Help: Working with abapGit on BTP](https://help.sap.com/docs/BTP/65de2977205c403bbc107264b8eccf4b/1bcf9be53bb44fa7848f325d7efc4e33.html) | **`VERIFIED`** | Supported strictly for custom ABAP development objects (`ZCL_*`, `ZIF_*`) in customer software packages. |
| **ABAP Cloud Routine Wrapping** | Restricted ABAP for Cloud | [SAP Help: ABAP Cloud Model](https://help.sap.com/docs/BTP/65de2977205c403bbc107264b8eccf4b/f746eb988e0b4924b10b064c1bfa7075.html) | **`VERIFIED_WITH_PREREQUISITES`** | Valid strategy. HANAMORPH can generate BTP ABAP Cloud-compliant class wrappers for routines. |

---

## 5. SAP Business Data Cloud (BDC) Capabilities Matrix

| Capability | Official SAP Interface | Official SAP Reference URL | Verification Status | Architectural Reality & Constraints |
| :--- | :--- | :--- | :---: | :--- |
| **BW Data Subscriptions** | SAP BW Cockpit (Fiori App) | [SAP Help: BW Data Subscriptions](https://help.sap.com/docs/SAP_BW4HANA/ed919380760a44388ab90e6bb3e7480a/4b5a3e145f8e4e7e8b6b23f2f7e7e6a1.html) | **`VERIFIED_WITH_PREREQUISITES`** | Requires SAP BW/4HANA 2021/2023 with current SP. Configured via SAP BW Cockpit UI, not external APIs. |
| **Data Sharing Cockpit** | SAP Datasphere Data Sharing Cockpit | [SAP Help: Data Sharing Cockpit](https://help.sap.com/docs/SAP_DATASPHERE/c8a5410afbbf4928ac78477215c0e178/e6b22c8cb93845dc8a113ecaa68a62f5.html) | **`VERIFIED`** | Governs product creation, consumer contracts, and access entitlements. |
| **Internal Class Integration** (`CL_RSO_DATA_PRODUCT`) | ABAP Internal Kernel Class | None | **`NOT_SUPPORTED`** | **PRIVATE CLASS:** Not an official public integration API or REST service. Prohibited for external tooling. |
| **Declarative Data Product Manifest** | Open Data Product Descriptor (`data-product.json`) | [SAP Help: Data Products in Datasphere](https://help.sap.com/docs/SAP_DATASPHERE/c8a5410afbbf4928ac78477215c0e178/3f7bf92e624b4df9977e0cebc06cb5eb.html) | **`VERIFIED`** | Valid declarative artifact format for packaging data product specifications. |

---

## 6. Hybrid Coexistence & Replication Capabilities Matrix

| Capability | Official SAP Interface | Official SAP Reference URL | Verification Status | Architectural Reality & Constraints |
| :--- | :--- | :--- | :---: | :--- |
| **Direct DB Change Log Extraction** | Table Read on `/BIC/AZSAM_SO012` | None | **`NOT_SUPPORTED / HAZARDOUS`** | Violates SAP architecture. Bypasses application locks, security filters, and delta request packaging (`REQTSN`). |
| **ODP-BW Extraction via Replication Flow** | SAP Datasphere Replication Flow + ODP Context | [SAP Help: ODP Integration in Datasphere](https://help.sap.com/docs/SAP_DATASPHERE/c8a5410afbbf4928ac78477215c0e178/5a91723e7f4c4c449c4f1c99852f86d8.html) | **`VERIFIED`** | **Official Supported Method:** Exposes ADSO as ODP InfoProvider. Replication Flow handles delta queue safely. |
| **Dual-Run Delta Coexistence** | ODP Delta Queue (`ODQMON`) + SAC Dual Reporting | [SAP Note 2481335 - Operational Data Provisioning FAQ](https://me.sap.com/notes/2481335) | **`VERIFIED`** | Standard enterprise cutover pattern. Source BW continues operational reporting while target tests in shadow mode. |
