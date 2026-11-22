# BW MIGRATION STUDIO — DATABASE & PERSISTENCE AUDIT
**Subject:** Database Schema, Versioned Migrations, WAL Concurrency & Data Integrity  
**Database File:** `BW_Migration_Studio/bw-studio/database/bw_studio.sqlite`  
**Status:** **AUDITED & VERIFIED**  

---

## 1. Database Architecture & Concurrency Model

The BW Migration Studio utilizes an embedded SQLite 3 database operating under strict enterprise reliability configurations:

```
+--------------------------------------------------------------------------------+
|                      SQLITE CONCURRENCY & WRITER ARCHITECTURE                  |
+--------------------------------------------------------------------------------+

   [ MULTIPLE CONCURRENT PRODUCERS ] (Discovery, Assessment, Planning, Validation)
                    |
                    | (Task / SQL Statements submitted)
                    v
          [ SingleWriterQueue ] (FIFO Queue, Thread-Safe)
                    |
                    | (Dedicated Serialized Worker Thread)
                    v
         [ WRITER CONNECTION ] ---> PRAGMA journal_mode = WAL;
                    |          ---> PRAGMA busy_timeout = 10000;
                    |          ---> PRAGMA synchronous = NORMAL;
                    |          ---> PRAGMA foreign_keys = ON;
                    v
    [ bw_studio.sqlite + bw_studio.sqlite-wal ]
```

### Key Concurrency Directives:
1. **SingleWriterQueue:** All mutating SQL queries are routed through a serialized background writer thread. This eliminates `sqlite3.OperationalError: database is locked` even under high producer concurrency.
2. **Dead-Letter Queue (DLQ):** Failed SQL writes that cannot be retried are isolated into an in-memory DLQ, allowing subsequent batch items to complete without blocking the pipeline.
3. **WAL Journal Mode:** Write-Ahead Logging allows concurrent readers to query the database simultaneously without blocking the active write thread.

---

## 2. Versioned Schema Migrations (Migrations 1 to 7)

All schema changes are tracked non-destructively in `database/schema_manager.py`:

| Migration # | Version Name | Tables & Views Created | Purpose |
| :--- | :--- | :--- | :--- |
| **Migration 1** | Base Core Tables | `schema_migrations`, `bw_systems`, `discovery_runs`, `bw_objects`, `bw_object_fields`, `bw_object_dependencies` | System catalog, discovery metadata, and fields |
| **Migration 2** | Assessment & Findings | `assessment_runs`, `assessment_findings` | Legacy 5-way assessment scoring and findings |
| **Migration 3** | Planning & Execution | `migration_projects`, `migration_plans`, `migration_plan_items` | Versioned plans, Kahn DAG sequence, approval status |
| **Migration 4** | Gen, Val, Pack, Logs | `generation_runs`, `generated_artifacts`, `validation_runs`, `validation_results`, `delivery_packages`, `system_connection_logs` | Code generation artifacts, 7-level checks, release seals |
| **Migration 5** | Backward Compatibility | Views: `catalog_objects`, `object_fields`, `dependencies`, `assessment_results` | Compatibility layer for legacy query contracts |
| **Migration 6** | Canonical Metadata | `canonical_bw_objects`, `canonical_object_fields`, `canonical_dependencies` | Structured URN identities, 15 attributes, provenance |
| **Migration 7** | Modernization Intel | `modernization_assessments`, `route_evaluations`, `complexity_breakdowns` | 7D complexity, 4 routes, 7-factor risk, effort hours |

---

## 3. Database Location Anomaly Finding

### Critical Observation:
During the filesystem audit, two distinct SQLite database files were discovered:
1. `BW_Migration_Studio/bw-studio/database/bw_studio.sqlite` (Active, 13 objects cataloged, contains all tables through Migration 7).
2. `BW_Migration_Studio/bw-studio/bw_studio.sqlite` (Legacy root copy, 4 objects cataloged, used by standalone script `verify_synthetic_e2e.py`).

### Audit Recommendation:
`verify_synthetic_e2e.py` line 18 must be updated to target `os.path.join(BASE_DIR, "database", "bw_studio.sqlite")` to ensure a single, authoritative database file exists across all execution contexts.
