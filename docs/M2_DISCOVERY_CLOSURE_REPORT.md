# HANAMORPH — M2 DISCOVERY CLOSURE REPORT
**Milestone:** M2 — Discovery and Metadata Foundation Closure  
**SAP System:** SAP BW S21 (NetWeaver AS ABAP 7.53, Client 200, Host 192.168.1.55)  
**Status:** **CLOSED & VERIFIED**  

---

## 1. Scope & Objective

The objective of Milestone M2 was to close all open requirements for source discovery against SAP BW 7.50 / NetWeaver 7.53 (`S21`) under strict read-only constraints, establish complete catalog normalization, and ensure high-fidelity schema extraction.

---

## 2. Discovery Channel Architecture

On SAP NetWeaver AS ABAP 7.53, discovery operates via two complementary, non-mutating mechanisms:

```
+--------------------------------------------------------------------------------+
|                        HANAMORPH DISCOVERY ARCHITECTURE                        |
+--------------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
  [ CHANNEL 1: LIVE ADT ]                        [ CHANNEL 2: BWMT CACHE ]
  - HTTP GET / HEAD Only                         - Local Eclipse Workspace
  - /sap/bc/adt/discovery (Status 200)           - .bw/ Metadata XML Files
  - /sap/bc/adt/repository/quicksearch           - Semantic Joins & Unions
  - /sap/bc/adt/ddic/tables/{name}               - BEx Queries & Variables
  - Live DDIC Fields & Types                     - Ingestion via IngestionEngine
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                     [ CANONICAL METADATA REPOSITORY ]
                     - URN: urn:sap:bw:s21:200:{type}:{name}
                     - SHA-256 Content Fingerprint
                     - Provenance: LIVE_VERIFIED vs CACHED
```

### Channel 1: Live ADT HTTP GET/HEAD Extraction
- **ADT Discovery:** `/sap/bc/adt/discovery` advertises 674 supported workspace collections.
- **ADT QuickSearch:** Queries `/sap/bc/adt/repository/quicksearch?operation=quickSearch&query=*ZSAM*&maxResults=50`. Verified: 10 live objects discovered with latency ~4.2s.
- **DDIC Table/View Field Extraction:** Calls `/sap/bc/adt/ddic/tables/{table_name}`. Verified on `/BIC/AZSAM_PR011` (14 fields extracted with SAP types `RSPM_REQUEST_TSN`, `CHAR`, `QUAN`, `UNIT`, lengths, decimals, key flags).

### Channel 2: Eclipse BWMT Workspace Ingestion
- NetWeaver AS ABAP 7.53 ICF nodes do not expose proprietary REST handlers for BWMT (`/sap/bc/adt/bw/*` returns 404).
- High-level semantic models (CompositeProvider join topologies, union projections, InfoObject attributes, BEx query formulas) are ingested from the developer's local Eclipse BW Modeling Tools workspace cache (`.bw/` XML files).
- The `IngestionEngine` normalizes these files into canonical schemas and assigns provenance `CACHED`.

---

## 3. Strict Read-Only Certification

All discovery pathways have been audited to guarantee **ZERO MUTATION** on SAP S21:
1. `BWConnectionManager.execute_sap_http()` hardcodes:
   ```python
   if method_upper not in ["GET", "HEAD"]:
       raise SecurityViolationError(f"Mutating HTTP method '{method_upper}' is forbidden.")
   ```
2. Unit tests and live integration tests explicitly attempt `POST` and `DELETE` requests and verify that `SecurityViolationError` is raised before any network packet is transmitted.
3. No CTS Transport Requests (`TRKORR`) are ever created, queried, or modified.
4. RFC execution is restricted strictly to benign ping functions (`RFC_PING`, `STFC_CONNECTION`).

---

## 4. Provenance Segregation

The repository strictly enforces provenance tags:
- `LIVE_VERIFIED`: Extracted live from SAP S21 via ADT HTTP GET.
- `CACHED`: Ingested from Eclipse BW Modeling Tools local workspace cache.
- `IMPORTED`: Loaded from external verified transport/metadata export bundles.
- `SYNTHETIC_OFFLINE`: Generated for isolated offline unit and integration tests.

Synthetic and cached metadata are never masqueraded as live verified records.
