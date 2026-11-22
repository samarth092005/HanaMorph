# HANAMORPH — SAP Datasphere Connection and Configuration Guide

## 1. PURPOSE & ARCHITECTURAL OVERVIEW
This document defines the configuration, authentication protocols, security guardrails, and read-only verification procedures for connecting HANAMORPH BW Migration Studio to an SAP Datasphere tenant.

SAP Datasphere serves as a primary modern target for migrated BW data warehouse models, supporting:
- Native Datasphere Spaces (Graphic and SQL Views, CSN definitions, Data Flows).
- SAP BW Bridge (ABAP-based ingestion and staging for legacy extractors).
- Business Data Cloud (BDC) data products and metadata federations.

---

## 2. STRICT READ-ONLY SAFETY GUARDRAIL
In strict compliance with HANAMORPH enterprise security policies:
- **No Remote Deployment**: HANAMORPH does not push or deploy artifacts directly to the Datasphere tenant via REST APIs or CLI unless explicitly authorized in deployment mode. By default, all operations are **Read-Only / Introspection Only**.
- **Local Artifact Delivery**: All target assets (CSN JSON schemas, SQL DDL statements, mapping documentation) are generated strictly to local workspace directories (`output/<project_id>/<plan_id>/`).
- **Credential Masking**: OAuth client secrets and credentials are fully redacted (`***MASKED***`) in all diagnostic reports, log outputs, and browser responses.

---

## 3. PREREQUISITES & AUTHENTICATION MECHANISMS

Connecting to SAP Datasphere requires an OAuth 2.0 client configured in the SAP BTP Subaccount / Datasphere Administration Console.

### 3.1 OAuth 2.0 Client Credentials Flow
- **Tenant URL**: `https://<tenant>.<region>.datasphere.cloud`
- **Token Endpoint**: `https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token`
- **Client ID & Client Secret**: Generated in Datasphere System Configuration > OAuth Clients.
- **Grant Type**: `client_credentials`
- **Required Scopes (Read-Only)**:
  - `openid`
  - `datasphere:space:read`
  - `datasphere:catalog:read`
  - `datasphere:metadata:read`

---

## 4. ENVIRONMENT CONFIGURATION (`.env`)

Configure the following variables in your `.env` file within `BW_Migration_Studio/bw-studio/.env`:

```env
# SAP Datasphere Tenant Configuration
DATASPHERE_HOST=mytenant.datasphere.cloud
DATASPHERE_PORT=443
DATASPHERE_USE_SSL=true
DATASPHERE_SPACE=MIGRATION_SPACE
DATASPHERE_CLIENT_ID=sb-datasphere-client!b12345
DATASPHERE_CLIENT_SECRET=your_datasphere_oauth_client_secret_here
DATASPHERE_TOKEN_URL=https://mytenant.authentication.eu10.hana.ondemand.com/oauth/token
DATASPHERE_API_VERSION=v1
DATASPHERE_TIMEOUT_SEC=20
```

---

## 5. CONNECTION TESTING & VALIDATION

### 5.1 Automated Connection Test via Backend API
Execute a `POST` request to the test endpoint:
```http
POST /api/connections/test
Content-Type: application/json

{
  "system_type": "DATASPHERE",
  "host": "mytenant.datasphere.cloud",
  "port": 443,
  "use_ssl": true,
  "space": "MIGRATION_SPACE",
  "client_id": "sb-datasphere-client!b12345",
  "client_secret": "your_datasphere_oauth_client_secret_here",
  "token_url": "https://mytenant.authentication.eu10.hana.ondemand.com/oauth/token"
}
```

### 5.2 Expected Diagnostic Response
```json
{
  "status": "CONNECTED",
  "system_type": "DATASPHERE",
  "host": "mytenant.datasphere.cloud",
  "space": "MIGRATION_SPACE",
  "latency_ms": 118,
  "auth_valid": true,
  "details": {
    "token_type": "Bearer",
    "expires_in": 43199,
    "scope": "datasphere:space:read datasphere:catalog:read",
    "space_accessible": true
  },
  "timestamp": "2026-11-21T20:25:00Z"
}
```

---

## 6. ARTIFACT HANDOFF AND DEPLOYMENT OPTIONS

HANAMORPH generates standard SAP CSN and SQL DDL representations that can be imported into SAP Datasphere using:
1. **Datasphere CLI**:
   ```bash
   datasphere spaces models import --space MIGRATION_SPACE --file ./output/PROJ_001/PLAN_001/ADSO_SALES_ACT.csn.json
   ```
2. **Datasphere Web IDE**:
   - Navigate to **Data Builder** > **Import CSN / JSON**.
   - Upload the sealed deployment zip file from `delivery/<project_id>/<version>/package.zip`.
3. **SAP BDC Data Product Registration**:
   - Register the sealed schema contracts into SAP Business Data Cloud catalog.
