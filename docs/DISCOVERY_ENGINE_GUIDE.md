# HANAMORPH — Discovery Engine Engineering Guide

## 1. PURPOSE & ARCHITECTURE
The Discovery Engine is responsible for extracting, parsing, and normalizing SAP BW metadata into the Canonical Metadata Model without altering or impacting source systems.

### 1.1 Discovery Modes & Provenance
The engine supports three operating modes, each tagged with an immutable provenance badge:
1. `LIVE_VERIFIED`: Directly extracted from a connected SAP system (e.g. S21) via read-only ADT/NetWeaver HTTP APIs and verified via network handshakes.
2. `CACHED`: Hydrated from previously discovered and stored metadata in `bw_studio.sqlite`.
3. `IMPORTED`: Loaded from external offline metadata bundles (JSON/XML export files) without network connectivity.

---

## 2. STRICT READ-ONLY SAFETY CONTROLS
When interacting with live SAP systems (such as `S21`):
- All network calls pass through `ADTDiscovery` or `BWConnectionManager`.
- Only HTTP `GET` and `HEAD` verbs are permitted. Attempting `POST`, `PUT`, `DELETE` immediately raises `SAPSecurityViolationError`.
- No SAP locks (`/sap/bc/adt/repository/locks`) or CTS workbench transport requests are created.
- RFC calls are strictly whitelisted to non-mutating diagnostics (`RFC_PING`, `STFC_CONNECTION`).

---

## 3. METADATA EXTRACTION SCOPE

The engine discovers and reconstructs complete SAP BW operational hierarchies:
1. **DataSources (`OSOA`, `RSDS`)**: Extraction interfaces, delta mechanisms, selection fields.
2. **InfoObjects (`IOBJ`)**: Characteristics, key figures, compounding, navigation attributes, conversion routines.
3. **DataStore Objects (`ADSO`, `ODSO`)**: Staging tables, active tables, change logs, partition specs, key definitions.
4. **Transformations (`TRFN`)**: Source-to-target field formulas, rule types (Direct, Constant, Initial, Formula, Routine).
5. **Data Transfer Processes (`DTP`)**: Filter selections, extraction modes (Full, Delta), packaging sizes.
6. **CompositeProviders (`HCPR`)**: Join criteria, union mappings, projection attributes.
7. **BEx / Analytic Queries (`ELEM`)**: Variables, calculated key figures, restricted key figures, structures.
8. **ABAP / AMDP Routines (`ROUT`)**: Start routines, end routines, field routines, expert routines with syntax analysis.
9. **Process Chains (`RSPC`)**: Predecessor/successor execution graphs, event triggers, scheduling info.

---

## 4. OFFLINE BUNDLE INGESTION WORKFLOW
For air-gapped or restricted environments, metadata can be ingested offline:
1. Prepare a JSON/XML bundle containing serialized canonical objects.
2. Ingest via API:
   ```bash
   curl -X POST http://localhost:4004/api/discovery/import \
     -H "Content-Type: application/json" \
     -d @sample_bw_bundle.json
   ```
3. The engine parses the payload, validates schema conformity, generates fingerprints with `package` integrity, assigns `provenance = 'IMPORTED'`, writes via `SingleWriterQueue`, and creates an immutable snapshot in `discovery_snapshots`.
