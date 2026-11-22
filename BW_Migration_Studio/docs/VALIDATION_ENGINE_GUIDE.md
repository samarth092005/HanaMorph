# HANAMORPH — Validation Engine & Delivery Packager Guide

## 1. 7-LEVEL VALIDATION FRAMEWORK

Before any generated migration bundle can be delivered or imported into SAP Datasphere, it must pass a rigorous 7-level automated validation suite comprising 119 discrete checks:

```
[Level 1: Syntax] ➔ [Level 2: Schema] ➔ [Level 3: Lineage] ➔ [Level 4: Delta]
       ➔ [Level 5: Business Rules] ➔ [Level 6: Security] ➔ [Level 7: Deployment]
```

### 1.1 Level 1: Syntax Validation
- Validates JSON parseability and UTF-8 encoding across all `.csn.json` files.
- Verifies SQL DDL syntax compliance against SAP HANA Cloud SQL parser grammar.

### 1.2 Level 2: Schema Integrity
- Validates that CSN files conform to `$schema: https://cap.cloud.sap/schemas/csn.json`.
- Confirms entity definitions, element types (`cds.String`, `cds.Decimal`), and primary key specifications.

### 1.3 Level 3: Lineage & Reference Integrity
- Verifies that all upstream source fields map to valid target elements.
- Confirms no orphan foreign keys or broken cross-object references in CompositeProvider views.

### 1.4 Level 4: Delta & Currency Behavior
- Verifies delta pointers (ODP, change-log timestamps).
- Ensures currency fields (`CURR`) have corresponding currency reference fields (`CUKY`).
- Ensures quantity fields (`QUAN`) have associated unit keys (`UNIT`).

### 1.5 Level 5: Business Rules & Calculation Consistency
- Validates converted mathematical formulas and CASE/WHEN logic.
- Verifies division-by-zero safeguards (`NULLIF(denom, 0)`).

### 1.6 Level 6: Security & Data Privacy
- Audits field definitions for sensitive attributes (PII, salary, bank details).
- Verifies that restricted fields have appropriate masking annotations.

### 1.7 Level 7: Deployment Readiness
- Confirms naming conventions conform to Datasphere space identifier limits (< 30 chars).
- Checks reserved keyword collisions against SAP HANA SQL reserved words.

---

## 2. SEVERITY TIERS & DELIVERY QUALITY GATES

Findings from validation are categorized into three severity levels:
- **`ERROR`**: Critical defects that prevent correct execution or import. **Blocks package delivery.**
- **`WARNING`**: Non-blocking deviations or recommendations (e.g. unindexed foreign keys).
- **`INFO`**: Informational annotations regarding optimization or modern features.

**Delivery Gate Rule**:
A project achieves `can_deliver = true` if and only if `failed_checks == 0` (zero `ERROR` items) and `quality_score >= 80.0`.

---

## 3. SEALED DELIVERY PACKAGER

When `/api/delivery/package` is invoked for an eligible project:
1. Gathers all generated `.csn.json`, `.sql`, and `_mapping.md` files from `output/<project_id>/<plan_id>/`.
2. Packages artifacts into a standalone, compressed ZIP archive: `delivery/<project_id>/<version>/package.zip`.
3. Injects an authoritative `manifest.json` containing:
   - Target route and Datasphere space.
   - List of packaged files with individual SHA-256 hashes.
   - Master package SHA-256 checksum.
   - Generator metadata and timestamp.
4. Records the sealed delivery bundle into the `delivery_packages` database table.
