# HANAMORPH BW MIGRATION STUDIO
# M4.2 CANONICAL METADATA MODEL SPECIFICATION

**Document Version:** 2.0.0  
**Status:** **AUTHORITATIVE DESIGN & IMPLEMENTATION SPECIFICATION**  
**Component:** `BW_Migration_Studio/bw-studio/models/canonical_model.py`  
**Milestone:** M4.2 (Transformation & Generation Intelligence)

---

## 1. Architectural Purpose

The **Canonical Metadata Model** serves as the universal, technology-agnostic intermediate representation for all SAP BW metadata extracted by the studio. It decouples the upstream extraction sources (live SAP ADT XML, RFC tables, offline JSON bundles, or legacy caches) from the downstream modernization engines (lineage, complexity, risk assessment, ABAP transformation, and target generation).

---

## 2. Uniform Resource Name (URN) Identity System

Every object in the landscape is assigned a deterministic, collision-proof URN following RFC 8141 conventions:

### URN Syntax
```
urn:sap:bw:<system_id>:<client>:<object_type>:<escaped_technical_name>[:<version>]
```

| Segment | Normalization Rule | Example |
| :--- | :--- | :--- |
| `system_id` | Lowercase alphanumeric string | `s21`, `bw_prod`, `synth_bw` |
| `client` | 3-digit zero-padded string | `200`, `010`, `001` |
| `object_type` | Lowercase standardized canonical acronym | `adso`, `hcpr`, `iobj`, `trfn`, `dtpa`, `elem` |
| `escaped_technical_name` | URL percent-encoded (RFC 3986) | `/BIC/AZSAM_PR01` -> `%2FBIC%2FAZSAM_PR01` |
| `version` (optional) | Uppercase lifecycle state: `A` (Active), `M` (Modified), `D` (Delivery), `T` (Transport) | `A` |

### Stable URN vs. Versioned URN
- **Stable URN:** `urn:sap:bw:s21:200:adso:ZSAM_SO01` (identifies object across lifecycle versions).
- **Versioned URN:** `urn:sap:bw:s21:200:adso:ZSAM_SO01:A` (identifies specific active revision).

---

## 3. Supported SAP BW Source Object Types

The canonical schema represents 16 distinct SAP BW metadata types:

| Object Type | Canonical Code | Description | Semantic Role |
| :--- | :---: | :--- | :--- |
| **Advanced DataStore Object** | `adso` | Core SAP BW/4HANA persistence layer | Persistent Staging, Standard, or Direct Write |
| **CompositeProvider** | `hcpr` | Virtual SQL union/join modeling layer | Consumption & Mart Layer |
| **Classic DataStore Object** | `odso` | Legacy 3-table persistence (Active, New, Change Log)| Staging & Data Consolidation |
| **InfoCube** | `cube` | Star-schema multi-dimensional cube | Legacy Multidimensional Storage |
| **InfoObject (Characteristic)** | `chao` | Master data entity (attributes, texts, hierarchies)| Business Dimension |
| **InfoObject (Key Figure)** | `kyfg` | Quantitative measurement (amounts, quantities)| Measure |
| **Transformation** | `trfn` | ETL mapping rules with routine logic | Business Logic & Transposition |
| **Data Transfer Process** | `dtpa` | Data execution runtime and filter controller | Orchestration & Loading Filter |
| **DataSource** | `osrc` | Source system interface extraction entity | Extraction Contract |
| **Process Chain** | `pc` | Scheduled batch job network | Workflow Automation |
| **Open ODS View** | `oov` | Virtual integration over external tables | External Federation |
| **BW BEx Query** | `elem` | Analytical reporting definition | Analytical Reporting Interface |
| **InfoSource** | `isrc` | Intermediate transformation layer | Staging Pipeline |
| **InfoSet** | `iset` | Classic join view over InfoProviders | Classical Virtual Join |
| **MultiProvider** | `mpro` | Classic union view over InfoProviders | Classical Virtual Union |
| **Hierarchy** | `hier` | Parent-child or leveled tree structures | Master Data Hierarchy |

---

## 4. Deterministic Content Fingerprinting & Provenance

To guarantee that target artifact generation and delivery packages are 100% reproducible:

### Content Fingerprint Algorithm
```python
canonical_payload = {
    "system_id": self.urn.system_id,
    "client": self.urn.client,
    "object_type": self.urn.object_type,
    "technical_name": self.urn.raw_technical_name,
    "version": self.urn.version,
    "description": self.description,
    "infoarea": self.infoarea,
    "package": self.package,
    "active_status": self.active_status,
    "fields": [f.to_dict() for f in sorted(self.fields, key=lambda x: (x.position, x.field_name))],
    "dependencies": sorted(self.dependencies, key=lambda x: (x.get("source_urn", ""), x.get("target_urn", ""))),
    "custom_attributes": dict(sorted(self.custom_attributes.items()))
}
fingerprint = hashlib.sha256(json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
```
- **Property:** The timestamp is explicitly excluded from the payload, so two extractions of identical metadata produce identical SHA-256 hashes.
- **Change Detection:** Any modification to fields, keys, data types, or relationships automatically triggers a new fingerprint, flagging downstream artifacts as stale.

### Provenance Tracking
Every canonical entity records:
- `provenance`: `LIVE_VERIFIED` (extracted from active SAP S21), `IMPORTED` (from offline JSON bundle), `SYNTHETIC` (test fixture), or `CACHED` (historical snapshot).
- `confidence_score`: Float between `0.0` and `1.0` indicating verification depth.
- `completeness_score`: Float between `0.0` and `1.0` measuring field and relation population.
- `extracted_at`: ISO 8601 UTC timestamp of extraction.
