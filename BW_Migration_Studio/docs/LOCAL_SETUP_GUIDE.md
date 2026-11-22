# HANAMORPH — Local Development & Setup Guide

## 1. SYSTEM REQUIREMENTS
- **Operating System**: Windows 10/11, macOS 12+, or Linux (Ubuntu 20.04+).
- **Python**: Version 3.10 to 3.12 (standard library + `urllib`, `sqlite3`, `threading`).
- **RAM**: Minimum 8 GB recommended (16 GB for large BW metadata catalogs).
- **Disk**: 2 GB free SSD space for SQLite WAL journals and generated artifacts.

---

## 2. REPOSITORY & DIRECTORY LAYOUT
The project is organized under `BW_Migration_Studio/bw-studio`:
```
BW_Migration_Studio/bw-studio/
├── backend/
│   ├── server.py               # REST API HTTP Server (port 4004)
│   ├── config.py               # Environment configuration loader
│   ├── logging_config.py       # Centralized audit and logging
│   └── connection_manager.py   # SAP / Datasphere connection handling
├── database/
│   ├── db.py                   # SQLite connection provider with WAL pragmas
│   ├── sqlite_queue.py         # Thread-safe SingleWriterQueue with DLQ
│   └── migrations/             # Schema migrations (001 - 006)
├── discovery/
│   └── discovery_engine.py     # Canonical metadata discovery & bundle import
├── assessment_engine/
│   └── assessment_engine.py    # 5-dimension scoring & 4-route analysis
├── planning_engine/
│   └── planning_engine.py      # DAG sequencing, wave allocation, approvals
├── generation_engine/
│   └── generation_engine.py    # CSN, SQL DDL, and mapping generators
├── validation_engine/
│   └── validation_engine.py    # 7-level validation engine (119 checks)
├── deployment/
│   └── delivery_packager.py    # Sealed ZIP packaging & manifest hashing
├── frontend/
│   ├── index.html              # Modern, tabbed SPA frontend
│   └── static/                 # CSS styles and JavaScript logic
└── tests/
    └── run_all_tests.py        # Complete automated test suite
```

---

## 3. INSTALLATION & STARTUP STEPS

### 3.1 Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cd C:\Users\samarth\BW-hanamorph\BW_Migration_Studio\bw-studio
Copy-Item .env.example .env
```

### 3.2 Initialize the Database & Run Migrations
```powershell
python -c "from database.db import init_db; init_db()"
```

### 3.3 Execute the Test Suite
Ensure all 69 tests pass cleanly:
```powershell
python tests\run_all_tests.py
```

### 3.4 Launch the HANAMORPH Server
```powershell
python backend\server.py
```
Open your browser and navigate to: `http://localhost:4004`
