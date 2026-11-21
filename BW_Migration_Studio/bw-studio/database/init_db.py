import sqlite3
import os
import json

db_dir = r"C:\Users\samarth\BW-hanamorph\BW_Migration_Studio\bw-studio\database"
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "bw_studio.sqlite")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Create Tables
cur.executescript("""
DROP TABLE IF EXISTS source_catalog;
CREATE TABLE source_catalog (
    name TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    description TEXT,
    infoarea TEXT,
    source_system TEXT DEFAULT 'S21',
    column_count INTEGER DEFAULT 0,
    has_custom_abap BOOLEAN DEFAULT 0,
    support_status TEXT DEFAULT 'SUPPORTED'
);

DROP TABLE IF EXISTS object_fields;
CREATE TABLE object_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    length INTEGER,
    decimals INTEGER DEFAULT 0,
    is_key BOOLEAN DEFAULT 0,
    description TEXT,
    FOREIGN KEY(object_name) REFERENCES source_catalog(name)
);

DROP TABLE IF EXISTS dependencies;
CREATE TABLE dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_object TEXT NOT NULL,
    dependent_object TEXT NOT NULL,
    dependency_type TEXT NOT NULL,
    cardinality TEXT DEFAULT '1:1'
);

DROP TABLE IF EXISTS assessment_results;
CREATE TABLE assessment_results (
    object_name TEXT PRIMARY KEY,
    recommended_route TEXT NOT NULL,
    native_score INTEGER,
    bridge_score INTEGER,
    bdc_score INTEGER,
    abap_complexity TEXT,
    blast_radius INTEGER,
    rationale TEXT,
    FOREIGN KEY(object_name) REFERENCES source_catalog(name)
);

DROP TABLE IF EXISTS migration_jobs;
CREATE TABLE migration_jobs (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    target_space TEXT NOT NULL,
    target_name TEXT NOT NULL,
    target_type TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

DROP TABLE IF EXISTS job_logs;
CREATE TABLE job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    log_level TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS connection_profiles;
CREATE TABLE connection_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    system_type TEXT NOT NULL,
    host TEXT NOT NULL,
    client_or_space TEXT,
    auth_type TEXT NOT NULL,
    is_read_only BOOLEAN DEFAULT 1,
    status TEXT DEFAULT 'CONFIGURED'
);
""")

# Seed mock catalog
objects = [
    ("ZSAM_SO_IA", "INFOAREA", "Sales Order InfoArea", "Root", "S21", 0, 0, "SUPPORTED"),
    ("ZSAM_SO01", "ADSO", "Sales Order Header & Item ADSO", "ZSAM_SO_IA", "S21", 13, 0, "SUPPORTED"),
    ("ZSAM_SO_CP", "COMPOSITE_PROVIDER", "Sales Order CompositeProvider", "ZSAM_SO_IA", "S21", 15, 0, "SUPPORTED"),
    ("ZSAM_MM_PR", "ADSO", "Purchase Requisition Line Items", "ZAIS_BW", "S21", 10, 0, "SUPPORTED"),
    ("ZAIS_BW", "INFOAREA", "BW Common Object Area", "Root", "S21", 0, 0, "SUPPORTED"),
    ("ZSAM_FI_GL01", "ADSO", "General Ledger Accounting Entries", "ZAIS_BW", "S21", 18, 1, "REVIEW_REQUIRED")
]

cur.executemany("INSERT INTO source_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?)", objects)

# Seed fields for ZSAM_SO01
fields_so01 = [
    ("ZSAM_SO01", "SALES_DOC", "CHAR", 10, 0, 1, "Sales Document Number"),
    ("ZSAM_SO01", "ITEM_NUM", "NUMC", 6, 0, 1, "Sales Document Item Number"),
    ("ZSAM_SO01", "DOC_TYPE", "CHAR", 4, 0, 0, "Order Type"),
    ("ZSAM_SO01", "SALES_ORG", "CHAR", 4, 0, 0, "Sales Organization"),
    ("ZSAM_SO01", "DISTR_CHAN", "CHAR", 2, 0, 0, "Distribution Channel"),
    ("ZSAM_SO01", "DIVISION", "CHAR", 2, 0, 0, "Division"),
    ("ZSAM_SO01", "CUSTOMER", "CHAR", 10, 0, 0, "Sold-to Party"),
    ("ZSAM_SO01", "MATERIAL", "CHAR", 18, 0, 0, "Material Number"),
    ("ZSAM_SO01", "DOC_DATE", "DATS", 8, 0, 0, "Creation Date"),
    ("ZSAM_SO01", "NET_VALUE", "CURR", 15, 2, 0, "Net Value"),
    ("ZSAM_SO01", "CURRENCY", "CUKY", 5, 0, 0, "Currency"),
    ("ZSAM_SO01", "ORDER_QTY", "QUAN", 13, 3, 0, "Order Quantity"),
    ("ZSAM_SO01", "SALES_UNIT", "UNIT", 3, 0, 0, "Unit of Measure")
]
cur.executemany("INSERT INTO object_fields (object_name, field_name, data_type, length, decimals, is_key, description) VALUES (?, ?, ?, ?, ?, ?, ?)", fields_so01)

# Seed dependencies
deps = [
    ("2LIS_11_VAHDR", "ZSAM_SO01", "EXTRACTS_INTO", "1:N"),
    ("2LIS_11_VAITM", "ZSAM_SO01", "EXTRACTS_INTO", "1:N"),
    ("ZSAM_SO01", "ZSAM_SO_CP", "PART_PROVIDER", "1:1"),
    ("ZSAM_SO_CP", "ZSAM_SO_Q001", "REPORTING_VIEW", "1:N"),
    ("2LIS_02_SCL", "ZSAM_MM_PR", "EXTRACTS_INTO", "1:1")
]
cur.executemany("INSERT INTO dependencies (source_object, dependent_object, dependency_type, cardinality) VALUES (?, ?, ?, ?)", deps)

# Seed connections
conns = [
    ("conn-s21", "SAP BW S21 (Client 200)", "SAP_BW", "s21.corp.internal:3300", "200", "Basic / SNC (int_samarth)", 1, "VERIFIED_READ_ONLY"),
    ("conn-dsp", "SAP Datasphere EU10 Tenant", "SAP_DATASPHERE", "ailien-test.eu10.hcs.cloud.sap", "SALES_ANALYTICS", "OAuth 2.0", 0, "SANDBOX_TARGET"),
    ("conn-local", "Local Development SQLite", "SQLITE", "localhost", "bw_studio.sqlite", "None", 0, "ACTIVE")
]
cur.executemany("INSERT INTO connection_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)", conns)

conn.commit()
conn.close()

print("Local SQLite database initialized at:", db_path)
