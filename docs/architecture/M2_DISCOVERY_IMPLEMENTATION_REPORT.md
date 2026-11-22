# HANAMORPH — Milestone M2 Discovery & Ingestion Report
## Evidence-Driven SAP BW Discovery Engine & Metadata Normalization

---

### DOCUMENT CONTROL
- **Document ID**: `HANAMORPH-M2-DISCOVERY-REPORT`
- **Milestone Target**: Milestone M2 (Discovery & Metadata Ingestion Engine)
- **Target Repository**: `BW_Migration_Studio/bw-studio`
- **Date**: November 2026
- **Auditor & Author Role**: Principal Enterprise Architect & SAP Integration Lead
- **Status**: **VERIFIED & IMPLEMENTED**

---

## 1. OBJECTIVE & EXECUTIVE SUMMARY

Milestone M2 establishes an enterprise-grade, read-only discovery engine that understands SAP BW, BW/4HANA, S21, and S/4HANA metadata landscapes without executing modifying operations on source environments.

Key achievements:
1. **Provenance Tracking**: Strict isolation between `LIVE_VERIFIED` (live ADT inspection), `CACHED` (Eclipse ADT metadata cache), and `IMPORTED` (external metadata JSON/XML bundles).
2. **12 Discovery Categories**:
   - `OSRC` (DataSources)
   - `IOBJ` (InfoObjects)
   - `ADSO` (Advanced DataStore Objects: Standard, Staging, Direct Update)
   - `ISRC` (InfoSources)
   - `TRFN` (Transformations)
   - `DTPA` (Data Transfer Processes)
   - `RSPC` (Process Chains)
   - `HCPR` (CompositeProviders)
   - `ELEM` (BW Queries)
   - `ROUT` (ABAP/AMDP Routines)
   - `LINEAGE` (Data Lineage & Dependencies)
   - `DELTA` (Delta / History Loading & Semantics)
3. **Canonical Normalization**: Discovered assets are normalized into `CanonicalObject`, `CanonicalField`, `CanonicalURN`, and `CanonicalDependency` with SHA-256 fingerprinting.
4. **Resilience & Storage**: Atomic multi-statement writes routed through `SingleWriterQueue` with concurrent multi-reader access via SQLite WAL mode.

---

## 2. ARCHITECTURAL EXTRACTION MATRIX

| Category | Source Interface | Extraction Strategy | Provenance Classification | Field Schema Extraction |
| :--- | :--- | :--- | :--- | :--- |
| **ADSO** | NetWeaver ADT REST (`/sap/bc/adt/ddic/tables/`) + XML cache | Dynamic table inspection (`/BIC/A<name>2`) | `LIVE_VERIFIED` or `CACHED` | Full fields, types, lengths, keys |
| **CompositeProvider (HCPR)** | Eclipse ADT XML (`model.composite`) | XML tree parsing of Join/Union nodes | `CACHED` | Mapped attributes & star schema |
| **BW Query (ELEM)** | Eclipse ADT XML (`model.query`) + BEx runtime | Query structure introspection | `CACHED_PARTIAL` | Measures, dimensions, variables |
| **InfoSource (TRCS)** | Eclipse ADT XML (`model.trcs`) | XML schema element extraction | `CACHED` | 11 semantic fields with lengths |
| **DataSource (OSRC)** | Lineage extraction & TRFN source | Extractor metadata inspection | `CACHED` or `IMPORTED` | Extraction fields & delta type |
| **External Bundles** | REST Ingestion (`/api/discovery/import`) | JSON/XML schema ingestion | `IMPORTED` | Full structured payload |

---

## 3. CANONICAL NORMALIZATION PIPELINE

Discovered metadata is transformed into canonical models without data loss:
1. **Identity**: Normalized URN formatted as `urn:sap:bw:<system>:<client>:<type>:<escaped_name>:<version>`.
2. **Structural Fingerprint**: SHA-256 computed deterministically over semantic payload including package, fields, and dependencies.
3. **Confidence Scoring**: 
   - `LIVE_VERIFIED`: 0.95 - 1.00
   - `CACHED`: 0.85 - 0.90
   - `IMPORTED`: 0.95
   - `PARTIAL`: 0.50

---

## 4. VERIFICATION EVIDENCE

- Automated test `test_import_metadata_bundle` PASSED.
- Automated tests `test_cache_adapter_adso_dynamic_key_detection`, `test_cache_adapter_trcs_full_schema`, and `test_cache_adapter_query_partial_provenance` PASSED.
- End-to-end catalog and lineage integration verified under `test_end_to_end_engines.py`.
