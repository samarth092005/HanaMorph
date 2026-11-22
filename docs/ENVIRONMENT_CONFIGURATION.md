# HANAMORPH — Environment Configuration Reference

## 1. OVERVIEW
HANAMORPH loads runtime configuration from `.env` located in `BW_Migration_Studio/bw-studio/.env`. Environment variables override default fallback settings defined in `backend/config.py`.

---

## 2. COMPLETE CONFIGURATION DICTIONARY

### 2.1 Server & Application Configuration
| Variable | Default Value | Description |
|---|---|---|
| `PORT` | `4004` | Local HTTP REST API port. |
| `HOST` | `127.0.0.1` | Local listening interface (`127.0.0.1` for local safety). |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `APP_AUTH_TOKEN` | `""` | Optional static API Bearer token for securing REST endpoints. |

### 2.2 Database Configuration
| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_PATH` | `bw_studio.sqlite` | Filepath to primary SQLite database. |
| `SQLITE_BUSY_TIMEOUT_MS` | `10000` | Busy timeout in milliseconds for SQLite locks. |
| `SQLITE_WAL_MODE` | `true` | Enables Write-Ahead Logging for high concurrency. |
| `SQLITE_QUEUE_CAPACITY` | `1000` | Max buffer capacity for `SingleWriterQueue`. |

### 2.3 SAP BW System S21 Configuration
| Variable | Default Value | Description |
|---|---|---|
| `BW_SYSTEM_ID` | `S21` | Identifier for the source SAP system. |
| `BW_HOST` | `10.0.0.50` | IP address or hostname of SAP NetWeaver instance. |
| `BW_INSTANCE` | `00` | SAP System Instance number (e.g. 00). |
| `BW_CLIENT` | `200` | SAP Client number for authentication. |
| `BW_USER` | `int_samarth` | Administrative read-only service account. |
| `BW_PASSWORD` | `""` | Password for service account. |
| `BW_AUTH_METHOD` | `BASIC` | Authentication mode (`BASIC`, `SNC`, `X509`). |
| `BW_USE_HTTPS` | `false` | Whether to communicate over HTTPS (port 44300) or HTTP (8000). |
| `BW_TIMEOUT_SEC` | `15` | Network timeout for ADT and NetWeaver ping requests. |
| `BW_STRICT_READONLY` | `true` | **CRITICAL**: Enforces strict read-only jail at connector layer. |

### 2.4 SAP Datasphere Configuration
| Variable | Default Value | Description |
|---|---|---|
| `DATASPHERE_HOST` | `""` | Datasphere tenant hostname (e.g., `tenant.datasphere.cloud`). |
| `DATASPHERE_PORT` | `443` | SSL Port for Datasphere REST endpoints. |
| `DATASPHERE_SPACE` | `MIGRATION_SPACE` | Target Datasphere space for CSN entities and views. |
| `DATASPHERE_CLIENT_ID` | `""` | OAuth 2.0 Client ID generated in Datasphere. |
| `DATASPHERE_CLIENT_SECRET` | `""` | OAuth 2.0 Client Secret. |
| `DATASPHERE_TOKEN_URL` | `""` | OAuth token URL (UAA service). |

### 2.5 SAP BTP Configuration
| Variable | Default Value | Description |
|---|---|---|
| `BTP_SUBACCOUNT_ID` | `""` | UUID of the SAP BTP Subaccount. |
| `BTP_DESTINATION_SERVICE_URL` | `""` | Destination service URL in Cloud Foundry. |
| `BTP_DESTINATION_CLIENT_ID` | `""` | Client ID for destination service key. |
| `BTP_DESTINATION_CLIENT_SECRET` | `""` | Client Secret for destination service key. |
| `BTP_TARGET_DESTINATION_NAME` | `S21_READONLY_HTTP` | BTP Destination pointing to on-premise S21. |
