# HANAMORPH BW MIGRATION STUDIO: DELIVERY PACKAGE SPECIFICATION
## Standard Delivery Bundle Structure, Cryptographic Manifest & Deployment Specification

---

## 1. Document Control & Objective

| Metadata | Details |
|---|---|
| **Document ID** | HM-SPEC-DELIVERY-PKG-V1 |
| **System** | HanaMorph — BW Migration & Modernization Studio |
| **Component** | Delivery Packager & Release Governance Engine |
| **Author** | Senior SAP BW Migration & Modernization Team |
| **Status** | APPROVED / FORMAL SPECIFICATION |
| **Package Format** | Autonomous Local Directory Bundle & Offline Archive |
| **Target Platforms** | SAP Datasphere, SAP HANA Cloud, SAP BW Bridge, SAP BDC Data Product |

This specification defines the standard structure, metadata schemas, cryptographic manifests, naming conventions, and dry-run execution requirements for all deployable packages produced by the HanaMorph BW Migration & Modernization Studio.

---

## 2. Package Architecture Principles

1. **Zero System Mutation during Packaging**:
   Packaging operates strictly in user-space or build environments. It requires zero live database connections, executes zero remote DDL/DML, and introduces zero temporary objects into SAP S21 or target clouds.
2. **Deterministic & Reproducible Builds**:
   Given identical approved migration plan items and schema definitions, the packaging engine produces identical artifacts.
3. **Cryptographic Verifiability**:
   Every artifact included within the delivery bundle is cataloged in `manifest.json` with its relative path, file byte size, and SHA-256 cryptographic checksum. A single bit alteration invalidates the bundle.
4. **Self-Contained & Transportable**:
   The package contains everything required for offline inspection, manual review, automated CI/CD pipeline ingestion, or CLI-based dry-run execution without external runtime dependencies.
5. **Separation of Target Platforms**:
   Artifacts are segregated into designated target directories (`datasphere/`, `hana_cloud/`, `documentation/`) with clear deployment scripts.

---

## 3. Delivery Directory File Layout

A delivery package created for Project `<project_id>` at version `v<version>` conforms to the following directory hierarchy:

```
delivery/
└── <project_id>/
    └── v<version>/
        ├── manifest.json                        # Root cryptographic manifest and metadata
        ├── DEPLOYMENT_README.md                 # Operator instructions, execution prerequisites, safety rules
        ├── datasphere/                          # SAP Datasphere artifacts
        │   ├── csn/                             # SAP Core Schema Notation v2.0 JSON definitions
        │   │   ├── <object_1>_csn.json
        │   │   └── <object_2>_csn.json
        │   ├── deploy_datasphere.sh             # Datasphere CLI deployment orchestration script
        │   └── deploy_datasphere.ps1            # Windows PowerShell deployment script
        ├── hana_cloud/                          # SAP HANA Cloud database artifacts
        │   ├── ddl/                             # Column table and calculation view DDL scripts
        │   │   ├── <object_1>_table.sql
        │   │   └── <object_2>_table.sql
        │   ├── deploy_hana.sql                  # Consolidated transaction-safe execution script
        │   └── deploy_hana.ps1                  # PowerShell execution harness
        └── documentation/                       # Lineage, field mapping, and audit documentation
            ├── mappings/                        # Source-to-target field mapping specifications
            │   ├── <object_1>_mapping.json
            │   └── <object_2>_mapping.json
            ├── LINEAGE_AND_DEPENDENCIES.md      # Topological migration graph and order
            └── VALIDATION_SUMMARY.md            # Sign-off report from 7-level validation engine
```

---

## 4. `manifest.json` Schema Specification

The `manifest.json` file is the central source of truth for package contents. It is generated automatically by `DeliveryPackager` upon completion of package staging.

### 4.1 Schema Definition
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "HanaMorphDeliveryManifest",
  "type": "object",
  "required": [
    "package_id",
    "project_id",
    "plan_id",
    "version",
    "created_at",
    "created_by",
    "approval_details",
    "summary",
    "files"
  ],
  "properties": {
    "package_id": { "type": "string", "pattern": "^pkg-[a-f0-9]{8}$" },
    "project_id": { "type": "string", "pattern": "^proj-[a-f0-9]{8}$" },
    "plan_id": { "type": "string", "pattern": "^plan-[a-f0-9]{8}$" },
    "version": { "type": "integer", "minimum": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "created_by": { "type": "string" },
    "approval_details": {
      "type": "object",
      "properties": {
        "status": { "type": "string", "enum": ["APPROVED"] },
        "approved_by": { "type": "string" },
        "approved_at": { "type": "string", "format": "date-time" },
        "notes": { "type": "string" }
      },
      "required": ["status", "approved_by"]
    },
    "summary": {
      "type": "object",
      "properties": {
        "total_files": { "type": "integer" },
        "total_bytes": { "type": "integer" },
        "target_platforms": { "type": "array", "items": { "type": "string" } },
        "validation_run_id": { "type": "string" },
        "validation_passed": { "type": "boolean" }
      },
      "required": ["total_files", "total_bytes", "target_platforms", "validation_passed"]
    },
    "files": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "relative_path": { "type": "string" },
          "sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
          "size_bytes": { "type": "integer", "minimum": 0 },
          "target_platform": { "type": "string" },
          "artifact_type": { "type": "string" }
        },
        "required": ["relative_path", "sha256", "size_bytes", "target_platform", "artifact_type"]
      }
    }
  }
}
```

### 4.2 Representative Example: `pkg-96390bd5`
```json
{
  "package_id": "pkg-96390bd5",
  "project_id": "proj-c55aec07",
  "plan_id": "plan-b3292be4",
  "version": 1,
  "created_at": "2026-11-21T06:58:34.908064Z",
  "created_by": "DeliveryPackager",
  "approval_details": {
    "status": "APPROVED",
    "approved_by": "Samarth (Architect)",
    "approved_at": "2026-11-21 06:57:38",
    "notes": "Approved for testing."
  },
  "summary": {
    "total_files": 39,
    "total_bytes": 105420,
    "target_platforms": ["Native Datasphere", "HANA Cloud"],
    "validation_run_id": "val-1e5afd51",
    "validation_passed": true
  },
  "files": [
    {
      "relative_path": "datasphere/csn/ZSAM_SO01_csn.json",
      "sha256": "47333ec1b73ddf9c75fe92a6b4122d1645e7308c397c6ff9ec8f9aeaf4df9a44",
      "size_bytes": 2840,
      "target_platform": "Native Datasphere",
      "artifact_type": "CSN_DEFINITION"
    },
    {
      "relative_path": "hana_cloud/ddl/ZSAM_SO01_table.sql",
      "sha256": "632ba36ba0ecab8942b0c360be1df591d63e9f4a0a4c2f6d2f36f6d0f507b927",
      "size_bytes": 1420,
      "target_platform": "HANA Cloud",
      "artifact_type": "HANA_DDL"
    }
  ]
}
```

---

## 5. Artifact Types & Encoding Specifications

### 5.1 Datasphere CSN JSON (`datasphere/csn/*.json`)
- **Format**: Valid JSON, UTF-8 without BOM.
- **Specification**: SAP Core Schema Notation v2.0 (`$schema: "https://help.sap.com/doc/csn-v2.0.json"`).
- **Naming Pattern**: `<OBJECT_NAME>_csn.json`.
- **Target Entity Naming**: `"<TARGET_SPACE>"."<TARGET_ENTITY>"`.
- **Elements Validation**: Every column must carry standard CDS data types (`cds.String`, `cds.Decimal`, `cds.Integer`, `cds.Date`, `cds.Timestamp`).
- **Semantics**: `@EndUserText.label`, `@Semantics.amount.currencyCode`, and `@Semantics.unitOfMeasure` must be preserved.

### 5.2 HANA Cloud Column Table DDL (`hana_cloud/ddl/*.sql`)
- **Format**: SQL script, UTF-8.
- **Target Syntax**: SAP HANA Cloud 2024+ SQL standard.
- **Naming Pattern**: `<OBJECT_NAME>_table.sql`.
- **Idempotency**: All DDL statements must be executable within a schema context (`SET SCHEMA "<TARGET_SPACE>";`). DDL MUST NOT use destructive drops (`DROP TABLE`) by default; migrations specify non-destructive alter/create semantics.
- **Key Constraints**: Primary keys must match source BW ADO/InfoObject key fields exactly.

### 5.3 Source-to-Target Mapping (`documentation/mappings/*.json`)
- **Format**: JSON, UTF-8 without BOM.
- **Naming Pattern**: `<OBJECT_NAME>_mapping.json`.
- **Content**: Explicit mapping array pairing `source_field`, `source_type`, `source_length` to `target_field`, `target_type`, `target_length`, with `transformation_rule` (e.g. `DIRECT_ASSIGNMENT`, `CAST`, `CONCATENATION`).

---

## 6. Deployment Scripts & Operational Safeguards

### 6.1 `deploy_datasphere.sh` / `deploy_datasphere.ps1`
- **Execution Mode**: Defaults to `--dry-run` or `--validate-only`.
- **CLI Dependency**: Requires official `@sap/datasphere-cli` authenticated with OAuth 2.0 client credentials.
- **Environment Isolation**: Checks target Space existence before attempting entity creation.
- **Safety Directive**: Halts immediately on the first API error (`set -e`).

### 6.2 `deploy_hana.sql` / `deploy_hana.ps1`
- **Execution Mode**: Dry-run syntax check by default.
- **Transactional Enclosure**: Script wraps operations in atomic transactions where supported or manages discrete object creation with prerequisite dependency verification.
- **Read-Only Protection**: The script enforces that the target database connection is explicitly restricted from altering SAP NetWeaver or ERP schema tables.

---

## 7. Delivery Package Verification Protocol

Before any package is certified for delivery or handoff to a customer, the following 4-step verification protocol is executed:

```
[Package Staged]
       │
       ▼
1. File Existence & Layout Check ─── (All required files present in hierarchy)
       │
       ▼
2. Checksum Integrity Check     ─── (Compute SHA-256 for all files, match manifest)
       │
       ▼
3. Plan Approval Verification   ─── (Verify plan status is APPROVED with sign-off)
       │
       ▼
4. Validation Run Linkage       ─── (Verify linked validation_run_id passed with 0 failures)
       │
       ▼
[Package Certified & Sealed]
```

If any check fails, the package is rejected and flagged as `TAMPERED` or `UNVERIFIED`.
