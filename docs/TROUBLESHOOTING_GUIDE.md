# HANAMORPH — System & Operational Troubleshooting Guide

## 1. PURPOSE
This guide provides diagnosis steps, error message catalogs, and resolution procedures for operational issues encountered while administering or operating HANAMORPH BW Migration Studio.

---

## 2. COMMON OPERATIONAL ISSUES & REMEDIATIONS

### 2.1 Server Startup & Network Port Conflicts
- **Symptom**: `OSError: [Errno 98] Address already in use` or `[Errno 10048]` on startup.
- **Root Cause**: Another process (or a previous HANAMORPH instance) is bound to port `4004`.
- **Remediation**:
  ```powershell
  # Locate process using port 4004
  netstat -ano | findstr :4004
  # Terminate process by PID
  Stop-Process -Id <PID> -Force
  # Or change port in .env: PORT=4005
  ```

### 2.2 Database Lock & Contention (`sqlite3.OperationalError: database is locked`)
- **Symptom**: Transactions fail with busy errors or timeout after 10 seconds.
- **Root Cause**: Direct unmanaged write operations bypassed `SingleWriterQueue` or a long-running manual SQLite shell holds an exclusive transaction lock.
- **Remediation**:
  1. Ensure WAL mode is active:
     ```powershell
     python -c "import sqlite3; con = sqlite3.connect('bw_studio.sqlite'); print(con.execute('PRAGMA journal_mode').fetchall())"
     ```
  2. Verify all write calls use `SingleWriterQueue.get_instance().execute_write(...)`.
  3. Close any external SQLite GUI tools (e.g. DB Browser for SQLite) holding exclusive locks.

### 2.3 Generation Engine Errors: `PLAN_NOT_APPROVED_ERROR` (HTTP 403)
- **Symptom**: Clicking "Generate Artifacts" yields an error stating the plan cannot be generated.
- **Root Cause**: Architecture plan is in `DRAFT` status. HANAMORPH enforces human approval as a quality gate before any artifacts are written.
- **Remediation**:
  - Open the **Planning** tab in the UI.
  - Review the topological DAG sequence and wave breakdown.
  - Click **Approve Plan** button to transition status to `APPROVED`.
  - Re-trigger artifact generation.

### 2.4 Dead-Letter Queue (DLQ) Inspection
- **Symptom**: Certain write operations silently failed or logs show items diverted to DLQ.
- **Inspection Command**:
  ```python
  from database.sqlite_queue import SingleWriterQueue
  q = SingleWriterQueue.get_instance("bw_studio.sqlite")
  print("DLQ Count:", len(q.get_dlq()))
  for item in q.get_dlq():
      print("Failed item:", item)
  ```
- **Remediation**: Analyze the failed SQL statements in the DLQ, correct any constraint violations or data typing mismatches, and call `q.clear_dlq()`.

### 2.5 Validation Engine Failures (`failed_checks > 0`)
- **Symptom**: Delivery packaging is blocked because `can_deliver = false`.
- **Remediation**:
  - Review the validation findings report via `/api/validation/results`.
  - Check for syntax errors or missing required primary key attributes in source metadata.
  - Update canonical model attributes or adjust field mappings to resolve `ERROR` severity items.
