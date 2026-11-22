# HANAMORPH — Canonical Metadata Model Specification

## 1. OBJECTIVE & DESIGN PRINCIPLES
The HANAMORPH Canonical Metadata Model provides a unified, vendor-agnostic abstraction layer for representing SAP BW metadata across disparate source architectures (BW 7.5 on AnyDB, BW 7.5 on HANA, BW/4HANA 1.0/2.0/2021/2023, and S/4HANA embedded BW).

Key Design Principles:
1. **Source Independence**: Normalizes heterogeneous SAP BW tables (`RSDODSO`, `RSDCUBE`, `RSTRAN`, `RSZELTXREF`) into standardized canonical classes.
2. **Deterministic Fingerprinting**: Every canonical object computes a deterministic SHA-256 fingerprint combining its package, technical name, TLOGO type, fields, and semantics.
3. **Audit Provenance**: Every object tracks its discovery origin (`LIVE_VERIFIED`, `CACHED`, `IMPORTED`).
4. **Target Portability**: Serves as the single source of truth for generating CSN JSON, SAP HANA SQL DDL, and Datasphere Data Flows.

---

## 2. CORE CANONICAL CLASSES

### 2.1 `CanonicalObject`
The root container representing an SAP BW metadata artifact:
- `object_id`: Unique identifier (`<system_id>:<tlogo_type>:<technical_name>`).
- `system_id`: Source system identifier (e.g., `S21`, `BW4`).
- `tlogo_type`: Standard SAP TLOGO type (`ADSO`, `HCPR`, `IOBJ`, `TRFN`, `DTP`, `ELEM`, `PC`).
- `technical_name`: Technical identifier in SAP (e.g., `ADSO_SALES_ACT`).
- `description`: Human-readable text / business label.
- `package`: ABAP Development Package / CTS Package (e.g., `Z_BW_FINANCE`).
- `provenance`: Origin badge (`LIVE_VERIFIED`, `CACHED`, `IMPORTED`).
- `fields`: List of `CanonicalField` definitions.
- `lineage`: List of upstream/downstream dependency links.
- `routines`: Custom ABAP / AMDP code blocks associated with the object.
- `custom_attributes`: Key-value metadata dictionary for source-specific extensions.

### 2.2 `CanonicalField`
Represents an individual column, characteristic, key figure, or navigational attribute:
- `name`: Technical field name.
- `datatype`: Canonical data type (`STRING`, `INTEGER`, `DECIMAL`, `DATE`, `TIMESTAMP`).
- `length`: Maximum field length.
- `precision` & `scale`: For decimal/currency/quantity figures.
- `is_key`: Boolean flag indicating primary key or dimensional key.
- `is_nullable`: Nullability constraint.
- `description`: Field label.
- `source_mapping`: Origin field name in transformation/DataSource.

### 2.3 `CanonicalLineage`
Models directed acyclic graph edges between canonical objects:
- `source_id`: Upstream object ID.
- `target_id`: Downstream object ID.
- `transformation_type`: Method of propagation (`DIRECT`, `ROUTINE`, `JOIN`, `UNION`, `LOOKUP`).
- `confidence`: Confidence score (0.0 to 1.0).

---

## 3. TLOGO TYPE CLASSIFICATION & TARGET MAPPINGS

| SAP TLOGO | Description | Canonical Class | Primary Datasphere Target | BW Bridge Target |
|---|---|---|---|---|
| `ADSO` | Advanced DataStore Object | `CanonicalObject (ADSO)` | Local Table / CSN Entity | Staging ADSO |
| `HCPR` | CompositeProvider | `CanonicalObject (HCPR)` | Graphical / SQL View | CompositeProvider |
| `IOBJ` | InfoObject (Char / Key Figure) | `CanonicalObject (IOBJ)` | Dimension / Text Table | InfoObject |
| `TRFN` | Transformation Rules | `CanonicalTransformation` | SQL View / Data Flow | ABAP Transformation |
| `DTP` | Data Transfer Process | `CanonicalObject (DTP)` | Data Flow / Replication Task | DTP |
| `ELEM` | BEx Query / Analytical Query | `CanonicalObject (ELEM)` | Analytical Model | Analytic Query |
| `PC` | Process Chain | `CanonicalObject (PC)` | Task Chain | Process Chain |

---

## 4. FINGERPRINTING ALGORITHM (Condition C-03 Fix)

To detect schema drift, code changes, or package reassignments, each object computes its content fingerprint as:
```python
def compute_fingerprint(self) -> str:
    payload = {
        "system_id": self.system_id,
        "tlogo_type": self.tlogo_type,
        "technical_name": self.technical_name,
        "package": self.package,  # Enforced by C-03 fix
        "fields": [
            {
                "name": f.name,
                "datatype": f.datatype,
                "length": f.length,
                "precision": f.precision,
                "scale": f.scale,
                "is_key": f.is_key
            } for f in sorted(self.fields, key=lambda x: x.name)
        ],
        "routines": [
            hashlib.sha256(r.code.encode('utf-8')).hexdigest()
            for r in self.routines
        ]
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
```
