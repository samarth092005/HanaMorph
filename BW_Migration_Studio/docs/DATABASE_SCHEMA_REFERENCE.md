# HANAMORPH — SQLite Database Schema & Concurrency Reference

## 1. ARCHITECTURE & CONCURRENCY MODEL

HANAMORPH utilizes an embedded SQLite 3 database (`bw_studio.sqlite`) engineered for concurrent multi-threaded workloads, zero-corruption reliability, and strict ACID guarantees.

### 1.1 Critical Connection PRAGMAs
Every database connection initialized by HANAMORPH applies:
```sql
PRAGMA journal_mode = WAL;          -- Write-Ahead Logging allows concurrent readers alongside 1 writer
PRAGMA busy_timeout = 10000;        -- 10-second wait before SQLITE_BUSY error
PRAGMA synchronous = NORMAL;        -- Optimal durability with minimal fsync overhead in WAL mode
PRAGMA foreign_keys = ON;           -- Enforces referential integrity on cascades and deletions
PRAGMA cache_size = -64000;         -- 64MB memory page cache for high-throughput metadata queries
```

### 1.2 SingleWriterQueue Architecture
To prevent `SQLITE_BUSY` contention across worker threads:
- **Write Serialization**: All mutating SQL queries (`INSERT`, `UPDATE`, `DELETE`) are submitted to a dedicated background writer thread via `SingleWriterQueue.get_instance(db_path)`.
- **Read Parallelism**: Reads (`SELECT`) execute concurrently using isolated, connection-pooled reader handles.
- **Dead-Letter Queue (DLQ)**: Malformed or failing writes are isolated into the DLQ without crashing the queue thread or blocking subsequent transactions.

---

## 2. SCHEMA MIGRATIONS (V1 TO V6)

Migrations are tracked in the `schema_migrations` table:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

1. **V1 (`001_initial_schema.sql`)**: Initial tables for canonical objects, lineage, and discovery runs.
2. **V2 (`002_assessment_tables.sql`)**: Multi-dimensional scoring, rule catalogs, and assessment runs.
3. **V3 (`003_planning_tables.sql`)**: Migration projects, architecture plans, DAG sequence mapping.
4. **V4 (`004_generation_tables.sql`)**: Artifact registry, CSN/SQL manifests, SHA-256 checksums.
5. **V5 (`005_validation_delivery.sql`)**: 7-level validation checks, severity levels, sealed delivery bundles.
6. **V6 (`006_provenance_snapshots.sql`)**: Added `provenance` (`LIVE_VERIFIED`, `CACHED`, `IMPORTED`), snapshot tables, and composite content fingerprints.

---

## 3. CORE TABLES REFERENCE

### 3.1 `canonical_objects`
Stores normalized SAP BW metadata objects across all types (`ADSO`, `TLOGO`, `IOBJ`, `ROUT`, `DTP`, `ELEM`).
```sql
CREATE TABLE canonical_objects (
    object_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL,
    tlogo_type TEXT NOT NULL,
    technical_name TEXT NOT NULL,
    description TEXT,
    package TEXT,
    content_fingerprint TEXT NOT NULL,
    provenance TEXT DEFAULT 'CACHED',
    metadata_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 `object_lineage`
Defines upstream and downstream dependencies for topological DAG sequencing.
```sql
CREATE TABLE object_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_object_id TEXT NOT NULL,
    target_object_id TEXT NOT NULL,
    transformation_type TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_object_id) REFERENCES canonical_objects(object_id) ON DELETE CASCADE,
    FOREIGN KEY(target_object_id) REFERENCES canonical_objects(object_id) ON DELETE CASCADE
);
```

### 3.3 `discovery_snapshots`
Records frozen, point-in-time snapshots of discovered metadata.
```sql
CREATE TABLE discovery_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    provenance TEXT NOT NULL,
    total_objects INTEGER NOT NULL,
    snapshot_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 `architecture_plans`
Stores DAG migration plans, wave allocations, and approval states.
```sql
CREATE TABLE architecture_plans (
    plan_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    target_route TEXT NOT NULL,
    status TEXT DEFAULT 'DRAFT',
    topological_sequence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
```

### 3.5 `generated_artifacts`
Tracks locally generated CSN schemas, SQL DDL files, and mapping docs.
```sql
CREATE TABLE generated_artifacts (
    artifact_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    object_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.6 `delivery_packages`
Sealed migration bundles ready for import into Datasphere or BW Bridge.
```sql
CREATE TABLE delivery_packages (
    package_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    version TEXT NOT NULL,
    archive_path TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    sha256_checksum TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
