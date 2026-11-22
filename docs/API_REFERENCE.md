# HANAMORPH — REST API Reference Guide

## 1. OVERVIEW & BASE URL
HANAMORPH BW Migration Studio exposes a high-performance REST API over HTTP/JSON for managing discovery, assessments, architecture planning, artifact generation, validation, and package delivery.

- **Base URL**: `http://localhost:4004`
- **Content-Type**: `application/json`
- **Authentication**: Bearer Token or Session Cookie (configured via `APP_AUTH_TOKEN`)

---

## 2. API ENDPOINTS SUMMARY

### 2.1 System & Connectivity
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Returns server health, uptime, and database WAL mode status. |
| `GET` | `/api/version` | Returns software version, build hash, and active milestones. |
| `GET` | `/api/connections` | Lists configured source (S21, BW) and target (Datasphere, BTP) profiles. |
| `POST` | `/api/connections/test` | Validates read-only connectivity to specified system with masked credentials. |

### 2.2 Discovery Engine (M2)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/discovery/runs` | Returns historical discovery execution runs and timestamps. |
| `POST` | `/api/discovery/start` | Initiates a discovery scan (`LIVE_VERIFIED` or `CACHED` mode). |
| `GET` | `/api/discovery/status` | Queries the current progress and object counters of an active scan. |
| `GET` | `/api/discovery/objects` | Retrieves canonicalized metadata objects with optional type filter (`ADSO`, `TLOGO`, etc.). |
| `POST` | `/api/discovery/import` | Ingests offline JSON/XML metadata bundles (`IMPORTED` provenance). |
| `GET` | `/api/discovery/snapshots` | Lists point-in-time canonical metadata snapshots with SHA-256 fingerprints. |

### 2.3 Assessment Engine (M3)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/assessment/runs` | Returns historical assessment runs. |
| `POST` | `/api/assessment/start` | Runs multi-dimensional assessment on discovered canonical objects. |
| `GET` | `/api/assessment/status` | Returns progress and current status of assessment engine. |
| `GET` | `/api/assessment/results` | Returns detailed scores, 4-route recommendations, and complexity tiers. |

### 2.4 Planning & Architecture Engine (M4)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/projects` | Lists all modernization projects. |
| `POST` | `/api/projects` | Creates a new migration project. |
| `GET` | `/api/projects/<id>/plans` | Returns generated architecture plans and DAG sequences. |
| `POST` | `/api/projects/<id>/plans` | Generates an architecture plan with target route selection. |
| `POST` | `/api/projects/<id>/plans/<plan_id>/approve` | Approves an architecture plan (required gate before generation). |

### 2.5 Generation Engine (M5)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generation/generate` | Generates local CSN schemas, SQL DDL, and mapping specifications. |
| `GET` | `/api/generation/artifacts` | Lists generated artifacts for a project and plan. |

### 2.6 Validation Engine (M6)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/validation/run` | Executes 7-level validation checks (Syntax, Schema, Lineage, Delta, Rules, Security, Dep). |
| `GET` | `/api/validation/results` | Retrieves validation findings, severities (`ERROR`, `WARNING`, `INFO`), and score. |

### 2.7 Delivery & Packaging (M6)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/delivery/package` | Compiles validated artifacts into a sealed ZIP package with SHA-256 manifest. |
| `GET` | `/api/delivery/packages` | Lists sealed delivery packages and checksums. |
| `GET` | `/api/delivery/download/<filename>` | Downloads the sealed `.zip` package. |

---

## 3. SAMPLE PAYLOADS & RESPONSES

### 3.1 `POST /api/projects/<id>/plans` (Generate Architecture Plan)
**Request Body**:
```json
{
  "project_id": "PROJ_BW_CORP",
  "name": "Global Sales & Finance Migration",
  "target_route": "native_datasphere",
  "scope_objects": ["ADSO_SALES_ACT", "CP_SALES_GL", "IO_CUSTOMER"]
}
```

**Response (200 OK)**:
```json
{
  "status": "SUCCESS",
  "plan_id": "PLAN_20261121_001",
  "project_id": "PROJ_BW_CORP",
  "target_route": "native_datasphere",
  "status_state": "DRAFT",
  "total_objects": 3,
  "topological_sequence": ["IO_CUSTOMER", "ADSO_SALES_ACT", "CP_SALES_GL"],
  "waves": [
    {"wave": 1, "objects": ["IO_CUSTOMER"]},
    {"wave": 2, "objects": ["ADSO_SALES_ACT"]},
    {"wave": 3, "objects": ["CP_SALES_GL"]}
  ]
}
```

### 3.2 `POST /api/validation/run`
**Response (200 OK)**:
```json
{
  "status": "VALIDATED",
  "project_id": "PROJ_BW_CORP",
  "total_checks": 119,
  "passed_checks": 119,
  "failed_checks": 0,
  "quality_score": 100.0,
  "can_deliver": true
}
```
