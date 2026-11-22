# HANAMORPH — System Administration & Operations Guide

## 1. PURPOSE & ADMINISTRATIVE ROLES
This guide covers administrative procedures, database lifecycle management, log rotation, security compliance audits, and maintenance tasks for HANAMORPH BW Migration Studio.

---

## 2. DATABASE LIFECYCLE & MAINTENANCE

### 2.1 Online Database Backups
SQLite WAL mode allows safe, live database backups without stopping the application or locking out concurrent readers:
```powershell
python -c "import sqlite3; con = sqlite3.connect('bw_studio.sqlite'); bck = sqlite3.connect('bw_studio_backup.sqlite'); con.backup(bck); print('Backup completed successfully.')"
```

### 2.2 WAL Checkpointing & Compaction (Vacuum)
To consolidate Write-Ahead Log files (`bw_studio.sqlite-wal`) and optimize disk layout:
```sql
PRAGMA wal_checkpoint(TRUNCATE);
VACUUM;
```

---

## 3. LOGGING, AUDITING & MONITORING

### 3.1 Log File Locations
All operational logs are stored in `BW_Migration_Studio/bw-studio/logs/`:
- `server.log`: Application runtime events, HTTP request access logs, and worker health.
- `connection_audit.log`: Security audit trail recording all outbound connection tests, target systems, latency, and status.
- `dead_letter_queue.log`: Detailed trace of any malformed write queries diverted by `SingleWriterQueue`.

### 3.2 Automated Credential Sanitization
Ensure that log analysis tools or SIEM forwarders observe zero cleartext credentials. HANAMORPH’s built-in log formatter automatically masks passwords, tokens, and client secrets with `***MASKED***`.

---

## 4. SCRATCH & ARTIFACT RETENTION POLICIES

To prevent unbounded disk consumption over multiple migration iterations:
- **Output Artifacts**: `output/<project_id>/` contains generated `.csn.json` and `.sql` files. Superseded plans can be purged manually or via script after successful package delivery.
- **Delivery Packages**: `delivery/<project_id>/` stores immutable sealed ZIP archives and manifests. Retain archives according to enterprise change management retention guidelines.
- **Temporary Uploads**: Ingested JSON/XML metadata bundles are stored temporarily in memory during ingestion and parsed into canonical records before memory release.
