# HANAMORPH BW Migration & Modernization Studio
# SAP Interface & Catalog Evidence Matrix — Phase 2.1 Reconciliation

**Document Reference:** `BW-MIG-IFACE-2.1`  
**Status:** Approved Technical Interface Baseline  
**Classification:** SAP Enterprise Modernization Interface Evidence  
**Evaluation Date:** November 21, 2026  

---

## 1. Classification & Interface Governance Standards

To ensure architectural rigor, this matrix classifies every SAP interface, function module, and DDIC repository structure proposed for HANAMORPH.

### Interface Type Standard:
- **`PUBLIC_API`**: Officially released, documented SAP BAPI, REST service, or RFC supported across upgrade cycles.
- **`INTERNAL_DDIC_TABLE`**: Standard NetWeaver database table. Fully populated and reliable, but constitutes an internal implementation detail rather than an external API.
- **`INTERNAL_FUNCTION_MODULE`**: Unreleased ABAP function module. Usable for read-only inspection, but signature may change between support packages.
- **`RESTRICTED_SERVICE`**: Official SAP service restricted by specific license add-ons or developer authorizations.

---

## 2. Source Connectivity & Discovery Interface Matrix

| Interface / Object Name | Interface Type | Supported Releases | Auth Objects Required | Network & Protocol | Returned Metadata Coverage | Known Limitations | Suitability | Official SAP Source URL | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **`RFC_PING`** | `PUBLIC_API` | All SAP NetWeaver | `S_RFC` (`ACTVT=16`, `FUGR=SYST`) | TCP 3300 (RFC) | Zero payload. Confirms network and gateway handshake. | Does not validate application authorizations or component versions. | Diagnostic Handshake | [SAP Note 321743](https://me.sap.com/notes/321743) | **`VERIFIED`** |
| **`STFC_CONNECTION`** | `PUBLIC_API` | All SAP NetWeaver | `S_RFC` (`ACTVT=16`, `FUGR=SYST`) | TCP 3300 (RFC) | Echo string, SAP system ID, application server host name. | Diagnostic only; no BW metadata. | Diagnostic Handshake | [SAP Note 321743](https://me.sap.com/notes/321743) | **`VERIFIED`** |
| **ADT Discovery Endpoint** (`/sap/bc/adt/discovery`) | `PUBLIC_API` | BW 7.5 SP04+, BW/4HANA | `S_ADT_RES` (`ACTVT=03`) | HTTPS 443 / 8000 | Workspace XML, supported ADT collections, CSRF token. | Does not return BW object definitions directly. | Connection Handshake & Auth | [SAP Help: ADT Services](https://help.sap.com/docs/ABAP_PLATFORM_NEW/683d53ba421143179700697811395297/4ec9ef056e391014adc9fffe4e204223.html) | **`VERIFIED`** |
| **ADT Repository Node Structure** (`/sap/bc/adt/repository/nodestructure`) | `RESTRICTED_SERVICE` | BW 7.5 SP08+, BW/4HANA | `S_ADT_RES` (`ACTVT=03`), `S_DEVELOP` | HTTPS 443 / 8000 | Hierarchical package / InfoArea tree, child object technical names. | Designed for lazy-loaded Eclipse UI expansion; high round-trip overhead for 50k bulk sweeps. | Selective Deep Discovery | [SAP Help: ADT Modeling](https://help.sap.com/docs/SAP_BW4HANA/107a6e8a38b7414db5cda37eedb0f80f/b4f91244e0074f4b9812674e2a8be9a9.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **ADT BW Modeling ADSO Service** (`/sap/bc/adt/bw/modeling/adso/*`) | `PUBLIC_API` | BW 7.5 SP08+, BW/4HANA | `S_ADT_RES` (`ACTVT=03`), `S_RS_ADSO` (`ACTVT=03`) | HTTPS 443 / 8000 | Full ADSO XML: dimensions, fields, keys, data types, lengths, change log flag. | Requires active SICF node; payload size 15KB–60KB per ADSO. | Selective Deep Discovery | [SAP Help: BWMT ADSO](https://help.sap.com/docs/SAP_BW4HANA/107a6e8a38b7414db5cda37eedb0f80f/b4f91244e0074f4b9812674e2a8be9a9.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **ADT BW Modeling CompositeProvider Service** (`/sap/bc/adt/bw/modeling/compositeprovider/*`) | `PUBLIC_API` | BW 7.5 SP08+, BW/4HANA | `S_ADT_RES` (`ACTVT=03`), `S_RS_HCPR` (`ACTVT=03`) | HTTPS 443 / 8000 | Full HCPR XML: join graph, join conditions, union nodes, projections. | Complex join trees can produce 100KB+ XML. | Selective Deep Discovery | [SAP Help: BWMT HCPR](https://help.sap.com/docs/SAP_BW4HANA/107a6e8a38b7414db5cda37eedb0f80f/b4f91244e0074f4b9812674e2a8be9a9.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`RSOOBJECTS`** | `INTERNAL_DDIC_TABLE` | All BW Releases | `S_TABU_DIS` (`DICBERCLS=SS`) | DB / Read Function | TLOGO type, technical name, object version (`OBJVERS`), InfoArea, description. | Internal DDIC table; must be read via authorized read-only RFC or DB view. | **Full Inventory (Level 1)** | [SAP Help: BW Repository](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`RSADSO`** | `INTERNAL_DDIC_TABLE` | BW 7.4 SP08+, BW/4HANA | `S_TABU_DIS` (`DICBERCLS=SS`) | DB / Read Function | ADSO properties: `ADSO_TYPE`, `CHANGELOG`, `INBOUND`, `ACTIVATION`. | Internal DDIC table; does not contain detailed field lists. | Full Inventory & Sizing | [SAP Help: ADSO Metadata](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`RSADSOFIELD`** | `INTERNAL_DDIC_TABLE` | BW 7.4 SP08+, BW/4HANA | `S_TABU_DIS` (`DICBERCLS=SS`) | DB / Read Function | Field names, positions, key flags, data types, lengths, decimals, InfoObject references. | Does not contain calculated join trees. | Deep Discovery (ADSO Fields) | [SAP Help: ADSO Metadata](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`RSOCP`** | `INTERNAL_DDIC_TABLE` | BW 7.4 SP05+, BW/4HANA | `S_TABU_DIS` (`DICBERCLS=SS`) | DB / Read Function | CompositeProvider header definition, status, package, author. | Join topology stored as serialized XML in cluster/text table. | Full Inventory (CPs) | [SAP Help: HCPR Definition](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`RSTRAN` / `RSTRANRULE`** | `INTERNAL_DDIC_TABLE` | All BW Releases | `S_TABU_DIS` (`DICBERCLS=SS`) | DB / Read Function | Transformation headers, source/target links, rule types (11 fields in TRCS). | Routine source code stored in generated includes (`GP*`). | Deep Discovery (TRFN) | [SAP Help: Transformation Tables](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`ROOSOURCE`** | `INTERNAL_DDIC_TABLE` | All BW / S/4HANA | `S_TABU_DIS` (`DICBERCLS=SS`) | DB / Read Function | DataSource definition, extractor name, extraction method, delta capability. | Legacy SAPI format; does not describe modern CDS extractors. | Deep Discovery (Extractors) | [SAP Help: DataSource Directory](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`RSDODSO`** | `INTERNAL_DDIC_TABLE` | BW 7.0–7.5 (Legacy) | `S_TABU_DIS` (`DICBERCLS=SS`) | DB / Read Function | Classic DSO definition (Standard, Write-Optimized, Transactional). | Obsolete in BW/4HANA; used solely for legacy migration scoping. | Legacy Inventory Scoping | [SAP Help: Classic DSO](https://help.sap.com/docs/SAP_BW/107a6e8a38b7414db5cda37eedb0f80f/483584852e2a3b04e10000000a42189d.html) | **`VERIFIED_WITH_PREREQUISITES`** |
| **`RS_DTP_GET_DETAIL`** | `INTERNAL_FUNCTION_MODULE` | BW 7.x | `S_RFC` (`ACTVT=16`) | TCP 3300 (RFC) | DTP parameters: source, target, extraction mode (`FULL`, `DELTA`), error stack. | Non-public API. May change across Support Packages. | Deep Discovery (DTP) | None (Internal NetWeaver FM) | **`PARTIALLY_VERIFIED`** |

---

## 3. Authoritative Architectural Guidelines

1. **Clear Interface Separation:** HANAMORPH strictly distinguishes **Public APIs** (`RFC_PING`, `STFC_CONNECTION`, ADT REST `/sap/bc/adt/*`) from **Internal Implementation Details** (`RSOOBJECTS`, `RSADSO`, `RS_DTP_GET_DETAIL`).
2. **Read-Only Authorization Enforcement:** When querying internal DDIC tables via RFC or ADT, authorizations must be restricted to display mode (`ACTVT=03` on `S_TABU_DIS` with table authorization groups `&NC&` and `SS`).
3. **No Arbitrary Table Reads:** Generic execution of `RFC_READ_TABLE` without field and row length constraints is prohibited.
