# HANAMORPH — SAP BTP Integration and Connection Guide

## 1. PURPOSE & ARCHITECTURAL SCOPE
This guide describes the integration patterns, service bindings, authentication methods, and security controls for connecting HANAMORPH BW Migration Studio to SAP Business Technology Platform (SAP BTP) environments.

Within modern BW migration landscapes, SAP BTP provides:
- **Cloud Foundry Runtime / Kyma**: Hosting environments for custom services, integration middleware, and APIs.
- **SAP Destination Service**: Centralized management of secure HTTP, RFC, and mail destinations.
- **SAP Connectivity Service & Cloud Connector**: Secure reverse-tunnel connectivity to on-premise SAP BW 7.50 / S21 systems without opening inbound firewall ports.
- **SAP Authorization & Trust Management Service (XSUAA)**: Enterprise OAuth 2.0 / JWT token validation and role-based access control.

---

## 2. STRICT READ-ONLY & NON-MUTATING BTP POLICY
- **No Cloud Foundry Mutating Commands**: No automated CLI commands (`cf push`, `cf delete`, `cf create-service`, `cf bind-service`) are executed by HANAMORPH.
- **Introspection Only**: Interactions with SAP BTP APIs are limited to reading destinations (`GET /destination-configuration/v1/subaccountDestinations`) and checking token validity.
- **Zero S21 Impact**: Using SAP Cloud Connector to connect to on-premise S21 adheres strictly to the non-mutating HTTP and RFC whitelist policy.

---

## 3. SAP BTP SERVICE BINDINGS

When running HANAMORPH in a hybrid or containerized configuration that interfaces with SAP BTP services, the following service keys are utilized:

### 3.1 Destination Service (`destination`)
Provides credentials and connectivity configurations for remote SAP systems.
- **Key Parameters**: `uri`, `clientid`, `clientsecret`, `url` (token service).
- **Usage**: Retrieves connection properties for destination `S21_HTTP` or `DATASPHERE_REST` securely at runtime.

### 3.2 Connectivity Service (`connectivity`)
Enables HTTP/SOCKS proxy routing through the SAP Cloud Connector to on-premise hosts.
- **Key Parameters**: `onpremise_proxy_host`, `onpremise_proxy_port`, `clientid`, `clientsecret`.
- **Usage**: Establishes outbound proxy tunnel for inspecting on-premise SAP BW metadata.

### 3.3 XSUAA Service (`xsuaa`)
Handles OAuth 2.0 authentication and authorization scopes.
- **Required Scopes for HANAMORPH Operators**:
  - `HanaMorph.Viewer`: Read-only access to discovery catalogs, assessments, and validation reports.
  - `HanaMorph.Planner`: Ability to create projects, generate architecture plans, and run validation.
  - `HanaMorph.Approver`: Authorization to approve architecture plans for artifact generation.

---

## 4. ENVIRONMENT CONFIGURATION (`.env`)

Add the following BTP configurations to `.env`:

```env
# SAP BTP Cloud Foundry Environment
BTP_SUBACCOUNT_ID=11223344-5566-7788-99aa-bbccddeeff00
BTP_REGION=eu10
BTP_CF_API_URL=https://api.cf.eu10.hana.ondemand.com
BTP_DESTINATION_SERVICE_URL=https://destination-configuration.cfapps.eu10.hana.ondemand.com
BTP_DESTINATION_CLIENT_ID=sb-destination!b123
BTP_DESTINATION_CLIENT_SECRET=your_btp_destination_client_secret_here
BTP_DESTINATION_TOKEN_URL=https://subaccount.authentication.eu10.hana.ondemand.com/oauth/token
BTP_TARGET_DESTINATION_NAME=S21_READONLY_HTTP
```

---

## 5. CONNECTION TESTING & VALIDATION

### 5.1 Test Destination Resolution
```http
POST /api/connections/test
Content-Type: application/json

{
  "system_type": "BTP_DESTINATION",
  "destination_name": "S21_READONLY_HTTP",
  "client_id": "sb-destination!b123",
  "client_secret": "your_btp_destination_client_secret_here",
  "token_url": "https://subaccount.authentication.eu10.hana.ondemand.com/oauth/token",
  "service_url": "https://destination-configuration.cfapps.eu10.hana.ondemand.com"
}
```

### 5.2 Diagnostic Verification
```json
{
  "status": "CONNECTED",
  "system_type": "BTP_DESTINATION",
  "destination_name": "S21_READONLY_HTTP",
  "latency_ms": 142,
  "destination_resolved": true,
  "proxy_type": "OnPremise",
  "url": "http://virtual-s21-host:8000",
  "timestamp": "2026-11-21T20:25:00Z"
}
```
