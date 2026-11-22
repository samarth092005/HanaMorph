# HANAMORPH BW MIGRATION STUDIO
# MILESTONE M4.1 — DATABASE RECONCILIATION & PERSISTENCE UNIFICATION REPORT

**Report Date:** 2026-11-22  
**Evaluation Target:** SQLite Persistence Tier across `database/bw_studio.sqlite` and root `bw_studio.sqlite`  
**Status:** **RECONCILED & VERIFIED (Zero Data Loss)**

---

## 1. Executive Summary

During the Standalone Baseline Audit, two SQLite database files were identified in the repository:
1. `BW_Migration_Studio/bw-studio/database/bw_studio.sqlite` (Primary Canonical Database)
2. `BW_Migration_Studio/bw-studio/bw_studio.sqlite` (Legacy Root Copy)

To eliminate split-brain persistence risks while strictly upholding the non-destructive preservation directive, an empirical schema audit, table-by-table row count analysis, and verified backup were conducted. All missing records from the legacy root database were non-destructively merged into the canonical store, and `verify_synthetic_e2e.py` was redirected to use the canonical path. The legacy database file remains completely intact on disk.

---

## 2. Comparative Database Analysis

| Inspection Attribute | Canonical Database (`database/bw_studio.sqlite`) | Legacy Root Database (`bw_studio.sqlite`) |
| :--- | :--- | :--- |
| **File Path** | `BW_Migration_Studio/bw-studio/database/bw_studio.sqlite` | `BW_Migration_Studio/bw-studio/bw_studio.sqlite` |
| **File Size** | **9,768,960 bytes (~9.7 MB)** | **319,488 bytes (~319 KB)** |
| **Table Count** | **30 tables** | **23 tables** |
| **Schema Migrations** | 6 migrations applied (v1 through v6) | 6 migrations applied (v1 through v6) |
| **Discovered Objects** | **17 objects** (13 live verified S21 + 4 synthetic) | 4 objects (synthetic only) |
| **Canonical BW Objects** | 5 objects | 4 objects |
| **Discovered Fields** | 52 fields | 6 fields |
| **Object Dependencies** | 14 dependencies | 1 dependency |
| **Migration Projects** | **43 projects** | 9 projects (synthetic only) |
| **Migration Plans** | **42 plans** | 8 plans |
| **Plan Items** | 374 items | 14 items |
| **Generated Artifacts** | **1,131 artifacts** | 42 artifacts |
| **Validation Results** | **60,848 results** | 175 results |
| **Exclusive Tables** | `assessment_results`, `connection_profiles`, `dependencies`, `job_logs`, `migration_jobs`, `object_fields`, `source_catalog` | None |

### Key Findings
1. **Primary Production Ownership:** `database/bw_studio.sqlite` is the true production database utilized by `backend/server.py`, `database/schema_manager.py`, `tests/test_discovery_and_parsers.py`, and `tests/test_end_to_end_engines.py`.
2. **Legacy Origin:** `bw_studio.sqlite` in the studio root was an orphaned artifact created exclusively because `tests/verify_synthetic_e2e.py:33` had been hardcoded to `os.path.join(studio_dir, "bw_studio.sqlite")`.
3. **Data Completeness:** All 9 projects and synthetic objects in the root database were generated during previous verification runs of `verify_synthetic_e2e.py`.

---

## 3. Verified Atomic Backup Strategy

Prior to executing any reconciliation operations, atomic online backups were created using SQLite's transactional `backup()` API to guarantee complete zero-corruption copies independent of WAL locks or process state.

| Source Database | Backup Destination | Backup Size | Table Integrity Match |
| :--- | :--- | :--- | :---: |
| `database/bw_studio.sqlite` | `database/bw_studio.sqlite.m4_1_backup` | 9.7 MB | **100% (30/30 tables verified)** |
| `bw_studio.sqlite` | `bw_studio.sqlite.m4_1_backup` | 319 KB | **100% (23/23 tables verified)** |

*Integrity verification script executed via `verify_backup_integrity.py` asserting exact row count and schema parity across all 53 combined tables.*

---

## 4. Non-Destructive Reconciliation & Merge

A non-destructive synchronization script was executed to merge all records from `bw_studio.sqlite` into `database/bw_studio.sqlite` using `INSERT OR IGNORE`.

### Merge Execution Results
- `canonical_bw_objects`: 4 new synthetic objects merged (`ZSYNTH_ADSO_01`, `ZSYNTH_CP_01`).
- `bw_objects`: 4 new synthetic records merged.
- `migration_projects`: 9 projects merged without collision.
- `migration_plans`: 8 plans merged.
- `generated_artifacts`: 42 artifact records merged.
- `validation_runs`: 7 validation runs merged.
- `discovery_runs`: 10 runs merged.
- `discovery_snapshots`: 4 new snapshot entries merged.
- `schema_migrations`: 0 conflicting rows; schema definitions matched identically.

---

## 5. Path Unification & Regression Verification

### Code Modification
In `tests/verify_synthetic_e2e.py`:
```python
# Before
db_path = os.path.join(studio_dir, "bw_studio.sqlite")

# After
db_path = os.path.join(studio_dir, "database", "bw_studio.sqlite")
```

### Verification
Following the path redirection:
1. `tests/verify_synthetic_e2e.py` executed successfully against the canonical database with **37 checks executed, 36 passed, 0 failed, 1 warning (expected synthetic rule check)**.
2. Full test suite ran with **92/92 tests passing**.
3. Legacy `bw_studio.sqlite` was preserved intact without deletion, renaming, or movement.
