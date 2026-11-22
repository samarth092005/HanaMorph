import sqlite3
import os
import time

class SchemaManager:
    """
    Non-destructive, versioned database migration and schema manager.
    Enforces the zero data loss principle (NEVER uses DROP TABLE IF EXISTS).
    Provides 17 normalized entities supporting the complete 7-phase modernization lifecycle.
    """
    MIGRATIONS = [
        # Migration 1: Base Core Tables & Migration Tracking
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bw_systems (
            system_id TEXT PRIMARY KEY,
            client TEXT NOT NULL,
            host TEXT NOT NULL,
            http_port INTEGER DEFAULT 8000,
            rfc_port INTEGER DEFAULT 3300,
            status TEXT DEFAULT 'ACTIVE',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS discovery_runs (
            id TEXT PRIMARY KEY,
            system_id TEXT NOT NULL,
            run_mode TEXT DEFAULT 'FULL',
            status TEXT DEFAULT 'IN_PROGRESS',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            objects_discovered INTEGER DEFAULT 0,
            provenance TEXT DEFAULT 'LIVE_VERIFIED',
            error_summary TEXT
        );

        CREATE TABLE IF NOT EXISTS bw_objects (
            id TEXT PRIMARY KEY,
            system_id TEXT NOT NULL,
            technical_name TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            infoarea TEXT,
            package TEXT,
            original_system TEXT DEFAULT 'S21',
            changed_by TEXT,
            changed_at TEXT,
            provenance TEXT DEFAULT 'LIVE_VERIFIED',
            raw_xml TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(system_id, technical_name)
        );

        CREATE TABLE IF NOT EXISTS bw_object_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            length INTEGER,
            decimals INTEGER DEFAULT 0,
            is_key BOOLEAN DEFAULT 0,
            aggregation_type TEXT DEFAULT 'NONE',
            semantics TEXT,
            currency_unit_field TEXT,
            description TEXT,
            UNIQUE(object_name, field_name)
        );

        CREATE TABLE IF NOT EXISTS bw_object_dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_object TEXT NOT NULL,
            dependent_object TEXT NOT NULL,
            dependency_type TEXT NOT NULL,
            mapping_details TEXT,
            cardinality TEXT DEFAULT '1:1',
            UNIQUE(source_object, dependent_object, dependency_type)
        );
        """,

        # Migration 2: Assessment & Findings Tables
        """
        CREATE TABLE IF NOT EXISTS assessment_runs (
            id TEXT PRIMARY KEY,
            system_id TEXT NOT NULL,
            model_version TEXT DEFAULT '1.0.0',
            total_objects INTEGER DEFAULT 0,
            run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assessment_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_run_id TEXT NOT NULL,
            object_name TEXT NOT NULL,
            recommended_target TEXT NOT NULL,
            overall_score INTEGER NOT NULL,
            functional_score INTEGER NOT NULL,
            technical_score INTEGER NOT NULL,
            process_score INTEGER NOT NULL,
            role_score INTEGER NOT NULL,
            platform_score INTEGER NOT NULL,
            complexity TEXT DEFAULT 'MEDIUM',
            risk_level TEXT DEFAULT 'LOW',
            findings_json TEXT,
            rationale TEXT,
            UNIQUE(assessment_run_id, object_name)
        );
        """,

        # Migration 3: Migration Planning & Execution
        """
        CREATE TABLE IF NOT EXISTS migration_projects (
            id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            source_system TEXT NOT NULL,
            target_platform TEXT NOT NULL,
            status TEXT DEFAULT 'DRAFT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS migration_plans (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            status TEXT DEFAULT 'DRAFT',
            approved_by TEXT,
            approved_at TIMESTAMP,
            plan_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS migration_plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            sequence_order INTEGER NOT NULL,
            source_object TEXT NOT NULL,
            target_artifact TEXT NOT NULL,
            target_platform TEXT NOT NULL,
            strategy TEXT NOT NULL,
            complexity TEXT DEFAULT 'MEDIUM',
            risk TEXT DEFAULT 'LOW',
            status TEXT DEFAULT 'PLANNED',
            UNIQUE(plan_id, source_object)
        );
        """,

        # Migration 4: Generation, Validation & Delivery Tables
        """
        CREATE TABLE IF NOT EXISTS generation_runs (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            target_platform TEXT NOT NULL,
            status TEXT DEFAULT 'IN_PROGRESS',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            total_artifacts INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS generated_artifacts (
            id TEXT PRIMARY KEY,
            generation_run_id TEXT NOT NULL,
            source_object TEXT NOT NULL,
            target_name TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            file_path TEXT,
            content TEXT,
            checksum_sha256 TEXT NOT NULL,
            validation_status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS validation_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_checks INTEGER DEFAULT 0,
            passed_checks INTEGER DEFAULT 0,
            failed_checks INTEGER DEFAULT 0,
            status TEXT DEFAULT 'IN_PROGRESS'
        );

        CREATE TABLE IF NOT EXISTS validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            validation_run_id TEXT NOT NULL,
            artifact_id TEXT,
            object_name TEXT,
            check_level INTEGER NOT NULL,
            check_category TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            expected TEXT,
            actual TEXT,
            evidence TEXT
        );

        CREATE TABLE IF NOT EXISTS delivery_packages (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            version TEXT NOT NULL,
            package_path TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            checksum_sha256 TEXT NOT NULL,
            status TEXT DEFAULT 'GENERATED',
            approved_by TEXT,
            approved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actor TEXT DEFAULT 'SYSTEM',
            action TEXT NOT NULL,
            system_id TEXT,
            details_json TEXT,
            severity TEXT DEFAULT 'INFO'
        );
        """,

        # Migration 5: Compatibility Views for Legacy Studio Endpoints
        """
        CREATE VIEW IF NOT EXISTS source_catalog AS
        SELECT
            technical_name AS name,
            type,
            description,
            infoarea,
            original_system AS source_system,
            (SELECT COUNT(*) FROM bw_object_fields WHERE object_name = bw_objects.technical_name) AS column_count,
            CASE WHEN type = 'ADSO' AND technical_name LIKE '%ABAP%' THEN 1 ELSE 0 END AS has_custom_abap,
            'SUPPORTED' AS support_status
        FROM bw_objects;

        CREATE VIEW IF NOT EXISTS object_fields AS
        SELECT
            id,
            object_name,
            field_name,
            data_type,
            length,
            decimals,
            is_key,
            description
        FROM bw_object_fields;

        CREATE VIEW IF NOT EXISTS dependencies AS
        SELECT
            id,
            source_object,
            dependent_object,
            dependency_type,
            cardinality
        FROM bw_object_dependencies;

        CREATE VIEW IF NOT EXISTS assessment_results AS
        SELECT
            object_name,
            recommended_target AS recommended_route,
            functional_score AS native_score,
            technical_score AS bridge_score,
            process_score AS bdc_score,
            complexity AS abap_complexity,
            3 AS blast_radius,
            rationale
        FROM assessment_findings;
        """,

        # Migration 6: Canonical Metadata Model & URN Identity (Milestone M1)
        """
        CREATE TABLE IF NOT EXISTS canonical_bw_objects (
            urn TEXT PRIMARY KEY,
            stable_urn TEXT NOT NULL,
            system_id TEXT NOT NULL,
            client TEXT NOT NULL,
            object_type TEXT NOT NULL,
            technical_name TEXT NOT NULL,
            version TEXT DEFAULT 'A',
            description TEXT,
            infoarea TEXT,
            package TEXT,
            active_status TEXT DEFAULT 'A',
            content_fingerprint TEXT NOT NULL,
            provenance TEXT DEFAULT 'LIVE_VERIFIED',
            confidence_score REAL DEFAULT 1.0,
            completeness_score REAL DEFAULT 1.0,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_canonical_stable_urn ON canonical_bw_objects(stable_urn);
        CREATE INDEX IF NOT EXISTS idx_canonical_system_client ON canonical_bw_objects(system_id, client);
        CREATE INDEX IF NOT EXISTS idx_canonical_fingerprint ON canonical_bw_objects(content_fingerprint);

        CREATE TABLE IF NOT EXISTS canonical_object_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_urn TEXT NOT NULL,
            field_name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            position INTEGER DEFAULT 0,
            length INTEGER DEFAULT 0,
            decimals INTEGER DEFAULT 0,
            is_key BOOLEAN DEFAULT 0,
            aggregation TEXT DEFAULT 'NONE',
            semantics TEXT,
            currency_unit_field TEXT,
            compounding_parent TEXT,
            description TEXT,
            UNIQUE(object_urn, field_name),
            FOREIGN KEY (object_urn) REFERENCES canonical_bw_objects(urn) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_canonical_fields_urn ON canonical_object_fields(object_urn);

        CREATE TABLE IF NOT EXISTS canonical_dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_urn TEXT NOT NULL,
            target_urn TEXT NOT NULL,
            dependency_type TEXT NOT NULL,
            is_hard_dependency BOOLEAN DEFAULT 1,
            mapping_details TEXT,
            UNIQUE(source_urn, target_urn, dependency_type)
        );

        CREATE INDEX IF NOT EXISTS idx_canonical_dep_src ON canonical_dependencies(source_urn);
        CREATE INDEX IF NOT EXISTS idx_canonical_dep_tgt ON canonical_dependencies(target_urn);

        CREATE TABLE IF NOT EXISTS canonical_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            system_id TEXT NOT NULL,
            client TEXT NOT NULL,
            object_count INTEGER DEFAULT 0,
            snapshot_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Migration 7: Modernization Intelligence & Assessment Engine (Milestone M3)
        """
        CREATE TABLE IF NOT EXISTS modernization_assessments (
            id TEXT PRIMARY KEY,
            assessment_run_id TEXT NOT NULL,
            object_name TEXT NOT NULL,
            urn TEXT,
            feasibility_status TEXT NOT NULL,
            complexity_score INTEGER NOT NULL,
            complexity_category TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            recommended_route TEXT NOT NULL,
            recommended_approach TEXT,
            effort_low_hours REAL,
            effort_expected_hours REAL,
            effort_high_hours REAL,
            priority_tier TEXT DEFAULT 'STANDARD',
            confidence_score REAL DEFAULT 1.0,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(assessment_run_id, object_name)
        );

        CREATE INDEX IF NOT EXISTS idx_mod_assess_run ON modernization_assessments(assessment_run_id);
        CREATE INDEX IF NOT EXISTS idx_mod_assess_obj ON modernization_assessments(object_name);
        CREATE INDEX IF NOT EXISTS idx_mod_assess_route ON modernization_assessments(recommended_route);
        CREATE INDEX IF NOT EXISTS idx_mod_assess_priority ON modernization_assessments(priority_tier);

        CREATE TABLE IF NOT EXISTS route_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_run_id TEXT NOT NULL,
            object_name TEXT NOT NULL,
            route_id TEXT NOT NULL,
            compatibility_score INTEGER NOT NULL,
            feasibility TEXT NOT NULL,
            required_changes_json TEXT,
            technical_risks_json TEXT,
            unsupported_capabilities_json TEXT,
            estimated_effort_hours REAL,
            confidence REAL DEFAULT 1.0,
            evidence_json TEXT,
            UNIQUE(assessment_run_id, object_name, route_id)
        );

        CREATE INDEX IF NOT EXISTS idx_route_eval_obj ON route_evaluations(object_name);

        CREATE TABLE IF NOT EXISTS complexity_breakdowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_name TEXT NOT NULL,
            structural_score INTEGER,
            dependency_score INTEGER,
            transformation_score INTEGER,
            data_model_score INTEGER,
            semantic_score INTEGER,
            customization_score INTEGER,
            operational_score INTEGER,
            overall_score INTEGER NOT NULL,
            complexity_category TEXT NOT NULL,
            drivers_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(object_name)
        );
        """
    ]

    def __init__(self, db_path: str):
        self.db_path = db_path
        dir_name = os.path.dirname(os.path.abspath(db_path))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """
        Returns an optimized SQLite connection with WAL mode and safety pragmas.
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA busy_timeout = 10000;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        cur.execute("PRAGMA foreign_keys = ON;")
        return conn

    def verify_integrity(self) -> dict:
        """
        Executes PRAGMA integrity_check to confirm SQLite file consistency.
        """
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        is_ok = len(rows) == 1 and rows[0] == "ok"
        return {
            "status": "PASSED" if is_ok else "FAILED",
            "messages": rows
        }

    def checkpoint_wal(self, mode: str = "TRUNCATE") -> dict:
        """
        Executes PRAGMA wal_checkpoint to flush WAL log frames to main database.
        Modes: PASSIVE, FULL, RESTART, TRUNCATE.
        """
        mode_upper = mode.upper()
        if mode_upper not in ["PASSIVE", "FULL", "RESTART", "TRUNCATE"]:
            mode_upper = "TRUNCATE"
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(f"PRAGMA wal_checkpoint({mode_upper});")
        row = cur.fetchone()
        conn.close()
        # Returns: (busy, log_frames, checkpointed_frames)
        return {
            "mode": mode_upper,
            "busy": row[0] if row else 0,
            "log_frames": row[1] if row else 0,
            "checkpointed_frames": row[2] if row else 0
        }

    def apply_migrations(self):
        conn = self.get_connection()
        cur = conn.cursor()

        # Create migration tracking table if not present
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        cur.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cur.fetchall()}

        for i, sql in enumerate(self.MIGRATIONS, 1):
            if i not in applied:
                print(f"Applying database migration {i}...")
                cur.executescript(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (i, f"migration_v{i}")
                )
                conn.commit()

        conn.close()
        print("Database schema verified and up-to-date.")

    def seed_initial_verified_data(self):
        """
        Populate the database with verified S21 metadata and connection definitions
        using INSERT OR IGNORE to never overwrite or destroy existing data.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Seed system S21
        cur.execute("""
            INSERT OR IGNORE INTO bw_systems (system_id, client, host, http_port, rfc_port, status, description)
            VALUES ('S21', '200', '192.168.1.55', 8000, 3300, 'CONNECTED', 'SAP BW 7.50 on SAP HANA')
        """)

        # Seed known verified S21 objects
        objects = [
            ("obj-zsam-so01", "S21", "ZSAM_SO01", "ADSO", "Sales Order Header & Item DataStore", "ZSAM_SO_IA", "$TMP", "S21", "INT_SAMARTH", "2026-11-18", "LIVE_VERIFIED"),
            ("obj-zsam-so-cp", "S21", "ZSAM_SO_CP", "COMPOSITE_PROVIDER", "Sales Order CompositeProvider", "ZSAM_SO_IA", "$TMP", "S21", "INT_SAMARTH", "2026-11-18", "LIVE_VERIFIED"),
            ("obj-zsam-pr01", "S21", "ZSAM_PR01", "ADSO", "MM Purchase Requisition ADSO", "ZAIS_BW", "$TMP", "S21", "INT_SAMARTH", "2026-11-16", "LIVE_VERIFIED"),
            ("obj-zcp-ekpo", "S21", "ZCP_EKPO", "COMPOSITE_PROVIDER", "Purchase CP (PO Items)", "ZAIS_BW", "$TMP", "S21", "INT_SAMARTH", "2026-11-16", "LIVE_VERIFIED"),
            ("obj-zbw-q001", "S21", "ZBW_Q001", "BW_QUERY", "PO Analytics Query on ZCP_EKPO", "ZAIS_BW", "$TMP", "S21", "INT_SAMARTH", "2026-11-16", "LIVE_VERIFIED"),
            ("obj-zsam-so-ia", "S21", "ZSAM_SO_IA", "INFOAREA", "Sales & Distribution InfoArea", "Root", "$TMP", "S21", "INT_SAMARTH", "2026-11-18", "LIVE_VERIFIED")
        ]
        cur.executemany("""
            INSERT OR IGNORE INTO bw_objects (id, system_id, technical_name, type, description, infoarea, package, original_system, changed_by, changed_at, provenance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, objects)

        # Seed real verified fields for ZSAM_SO01
        so01_fields = [
            ("ZSAM_SO01", "ORDER_ID", "CHAR", 10, 0, 1, "NONE", "ORDER", None, "Sales Order ID (Primary Key)"),
            ("ZSAM_SO01", "CUST_NAME", "CHAR", 30, 0, 0, "NONE", "NAME", None, "Customer Name"),
            ("ZSAM_SO01", "CITY", "CHAR", 20, 0, 0, "NONE", "GEO", None, "Customer City"),
            ("ZSAM_SO01", "AMOUNT", "CURR", 15, 2, 0, "SUM", "AMO", "CURRENCY", "Total Order Net Amount"),
            ("ZSAM_SO01", "CURRENCY", "CUKY", 5, 0, 0, "NONE", "CURR_CODE", None, "Currency Code Key")
        ]
        cur.executemany("""
            INSERT OR IGNORE INTO bw_object_fields (object_name, field_name, data_type, length, decimals, is_key, aggregation_type, semantics, currency_unit_field, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, so01_fields)

        # Seed real verified fields for ZSAM_PR01
        pr01_fields = [
            ("ZSAM_PR01", "BANFN", "CHAR", 10, 0, 1, "NONE", "BANFN", None, "Purchase Requisition Number"),
            ("ZSAM_PR01", "BNFPO", "CHAR", 5, 0, 1, "NONE", "BNFPO", None, "Purchase Requisition Item"),
            ("ZSAM_PR01", "BSART", "CHAR", 2, 0, 0, "NONE", "BSART", None, "Requisition Document Type"),
            ("ZSAM_PR01", "MATNR", "CHAR", 18, 0, 0, "NONE", "MATNR", None, "Material Number"),
            ("ZSAM_PR01", "TXZ01", "CHAR", 40, 0, 0, "NONE", "TEXT", None, "Short Description Text"),
            ("ZSAM_PR01", "MENGE", "QUAN", 13, 3, 0, "SUM", "QTY", "MEINS", "Requisition Quantity"),
            ("ZSAM_PR01", "MEINS", "UNIT", 3, 0, 0, "NONE", "UOM", None, "Base Unit of Measure"),
            ("ZSAM_PR01", "WERKS", "CHAR", 4, 0, 0, "NONE", "PLANT", None, "Plant Key")
        ]
        cur.executemany("""
            INSERT OR IGNORE INTO bw_object_fields (object_name, field_name, data_type, length, decimals, is_key, aggregation_type, semantics, currency_unit_field, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pr01_fields)

        # Seed verified dependencies
        deps = [
            ("ZSAM_SO_DS", "ZSAM_SO01", "EXTRACTS_INTO", "DataSource ZSAM_SO_DS feeds ADSO ZSAM_SO01", "1:N"),
            ("ZSAM_SO01", "ZSAM_SO_CP", "PART_PROVIDER", "ADSO ZSAM_SO01 is Union PartProvider U1 in ZSAM_SO_CP", "1:1"),
            ("ZSAM_SO_CP", "ZBW_Q001", "REPORTING_PROVIDER", "CompositeProvider ZSAM_SO_CP is underlying provider for Query", "1:N"),
            ("ZSAM_PR_IS01", "ZSAM_PR01", "EXTRACTS_INTO", "InfoSource ZSAM_PR_IS01 transforms into ADSO ZSAM_PR01", "1:1"),
            ("ZSAM_PR01", "ZCP_EKPO", "PART_PROVIDER", "ADSO ZSAM_PR01 participates in Purchase CP ZCP_EKPO", "1:1")
        ]
        cur.executemany("""
            INSERT OR IGNORE INTO bw_object_dependencies (source_object, dependent_object, dependency_type, mapping_details, cardinality)
            VALUES (?, ?, ?, ?, ?)
        """, deps)

        conn.commit()
        conn.close()
