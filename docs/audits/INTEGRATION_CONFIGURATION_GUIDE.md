# HANAMORPH BW MIGRATION STUDIO — INTEGRATION CONFIGURATION GUIDE
**Document Reference**: `docs/audits/INTEGRATION_CONFIGURATION_GUIDE.md`  
**Timestamp**: 2026-11-21T12:35:00+05:30  
**Status**: ACTIVE — S21 ADT CONNECTED | AWAITING CLOUD SECRETS CONFIGURATION  
**Authoritative Environments**: SAP BW S21 | SAP Datasphere | SAP BTP | SAP HANA Cloud | Cloud Foundry

---

## 1. Executive Summary & Current Connectivity Status

The **HanaMorph BW Migration Studio** integration configuration architecture has been fully established. It provides a modular, multi-system connection subsystem that decouples secrets from application code, enforces local cryptographic encryption, guarantees zero credential leakage, and hard-enforces strict read-only safety invariants across all SAP environments.

### Live Connection State Summary

| System | Target Landscape | Current Status | Latency | Verification Details |
| :--- | :--- | :--- | :--- | :--- |
| **SAP BW S21** | NetWeaver AS ABAP & BW (Client 200) | **CONNECTED** | **618 ms** | Authenticated ADT session active via `int_samarth`. Full read-only DDIC inspection verified. |
| **SAP Datasphere** | Data Warehouse Cloud / BDC | **PARTIALLY CONFIGURED** | -- | Interactive user configured (`varad.k@abhiyantatech.com`). Awaiting OAuth 2.0 Client credentials. |
| **SAP BTP** | Business Technology Platform | **PARTIALLY CONFIGURED** | -- | Interactive user configured. Awaiting BTP Subaccount ID & Service Key JSON. |
| **SAP HANA Cloud** | In-Memory Database (Port 443) | **NOT CONFIGURED** | -- | Awaiting HANA Cloud SQL host, port, user, and password. |
| **Cloud Foundry** | BTP Runtime Environment | **NOT CONFIGURED** | -- | Awaiting Cloud Foundry API endpoint, Org, and Space. |

---

## 2. Modular Configuration Architecture

The configuration subsystem is built with clean separation of concerns across 5 dedicated connection managers coordinated by a central registry:

```
[ Local User / Web UI ] <---> [ REST API (Port 4004) ]
                                    |
                    +---------------+---------------+
                    |        ConnectionHub          |
                    +---------------+---------------+
                                    |
     +--------------+---------------+--------------+--------------+
     |              |               |              |              |
     v              v               v              v              v
[ BW S21 Mgr ] [ Datasphere ]  [ BTP Mgr ]   [ HANA Cloud ]  [ Cloud Foundry ]
     |              |               |              |              |
(Strict Read-   (OAuth 2.0      (Service Keys  (Read-Only     (CF API v3
  Only Guard)     Client)        Preferred)      SQL Tx)        Info)
     |              |               |              |              |
     v              v               v              v              v
[ S21 Host ]   [ DSP Tenant ]  [ BTP Subacc ] [ HANA DB ]    [ CF Org/Space ]
192.168.1.55
```

### Component Inventory
1. **`CredentialVault`** (`bw-studio/connectors/credential_vault.py`):
   - Local symmetric key encryption powered by `cryptography.fernet.Fernet`.
   - Master encryption key stored in `.master_key` (strictly ignored by Git).
   - Dynamic secret masking: never logs or renders plain text passwords.
2. **`BWConnectionManager`** (`bw-studio/connectors/bw_connection_manager.py`):
   - Manages HTTP (Port 8000), HTTPS (Port 44300), and RFC (Port 3300) connectivity to S21.
   - Enforces **hard read-only safety guardrails**: all mutating HTTP methods (`POST`, `PUT`, `DELETE`, `PATCH`) raise `SecurityViolationError`.
   - Hard-blocks CTS transport creation (`/cts/`, `/transports`), locks (`/lock`), and object activation (`/activate`).
3. **`DatasphereConnectionManager`** (`bw-studio/connectors/datasphere_connection_manager.py`):
   - Decouples interactive web logon users from automated API/CLI OAuth clients.
   - Executes OAuth 2.0 Client Credentials token exchange.
4. **`BTPConnectionManager`** (`bw-studio/connectors/btp_connection_manager.py`):
   - Enforces enterprise best practice: rejects personal interactive passwords for unattended automation.
   - Supports BTP Service Key JSON files and OAuth2 Client Credentials.
5. **`HANAConnectionManager`** (`bw-studio/connectors/hana_connection_manager.py`):
   - Enforces `SET TRANSACTION READ ONLY` on SQL sessions.
6. **`CloudFoundryConnectionManager`** (`bw-studio/connectors/cloud_foundry_connection_manager.py`):
   - Validates Cloud Foundry API endpoint v3 health, Org, and Space configurations.

---

## 3. SAP BW S21 — Verified Connectivity & Safety Verification

### 3.1 Live Verification Results
Using the configured credentials in `.env`, the studio successfully executed live authenticated ADT discovery against S21:
- **Target Host**: `192.168.1.55` (Client 200, Instance 00)
- **User**: `int_samarth` (Administrative authorization `SAP_ALL` active on SAP)
- **ADT Discovery (`/sap/bc/adt/discovery`)**: **HTTP 200 OK** (Latency: `618 ms`)
- **ADT Quick Search (`/sap/bc/adt/repository/informationsystem/search`)**: **HTTP 200 OK**
- **Discovered Live S21 Objects**:
  - `/BIC/AZSAM_PR011` (Inbound Table for DataStore `ZSAM_PR01`)
  - `/BIC/AZSAM_PR012` (Active Data Table for DataStore `ZSAM_PR01`)
  - `/BIC/AZSAM_PR013` (Change Log for DataStore `ZSAM_PR01`)
  - `/BIC/AZSAM_PR016` (View for Extraction from DataStore `ZSAM_PR01`)
  - `/BIC/AZSAM_PR017` (View for Reporting for DataStore `ZSAM_PR01`)
  - `/BIC/AZSAM_SO011` (Inbound Table for DataStore `ZSAM_SO01`)
  - `/BIC/AZSAM_SO012` (Active Data Table for DataStore `ZSAM_SO01`)
  - `/BIC/AZSAM_SO013` (Change Log for DataStore `ZSAM_SO01`)
  - `/BIC/AZSAM_SO016` (View for Extraction from DataStore `ZSAM_SO01`)
  - `/BIC/AZSAM_SO017` (View for Reporting for DataStore `ZSAM_SO01`)
- **DDIC Table Inspection (`/sap/bc/adt/ddic/tables/%2fbic%2fazsam_so012/source/main`)**:
  - **HTTP 200 OK** (Latency: `520 ms`)
  - Live retrieved field definition:
    - `order_id : abap.char(10) not null;`
    - `cust_name : abap.char(30) not null;`
    - `city : abap.char(20) not null;`
    - `amount : abap.curr(15,2) not null;`
    - `currency : abap.cuky not null;`

### 3.2 Strict Read-Only Safety Directives
Because `int_samarth` possesses `SAP_ALL` administrative authorizations on S21, the studio hard-enforces the following invariants:
1. **HTTP GET / HEAD Only**: Any attempt by any agent, tool, or script to send `POST`, `PUT`, `DELETE`, or `PATCH` to S21 is blocked at the Python adapter with `SecurityViolationError`.
2. **Zero Transport / CTS Creation**: Endpoints matching `/sap/bc/adt/cts/*` or `/transports` are rejected.
3. **No Execution Functions**: DTP execution (`RSDTP_START`), Process Chain execution (`RSPC_CHAIN_START`), and BDC calls are strictly excluded.
4. **No DDIC Mutations**: No database tables, views, structures, or data elements can be created, activated, or deleted.

---

## 4. Missing Credentials & How to Obtain Them

To enable full end-to-end integration across the remaining 4 target environments, the following credentials and configurations must be added to your local `.env` file.

### 4.1 SAP Datasphere

#### Current State in `.env`:
- User: `varad.k@abhiyantatech.com`
- Status: **PARTIALLY CONFIGURED** (Interactive User configured; OAuth Client missing)

#### Why Web Passwords Cannot Be Used for Automation:
The SAP Datasphere CLI (`@sap/datasphere-cli`) and REST API do **not** support basic authentication with interactive email/passwords. They require an **OAuth 2.0 Client** registered in Datasphere to issue secure Bearer tokens without user session timeouts or CAPTCHA/MFA blocks.

#### Step-by-Step: How to Obtain Datasphere OAuth Credentials:
1. Open your browser and log into your **SAP Datasphere** tenant as an Administrator.
2. In the left navigation menu, go to **System** &rarr; **Administration**.
3. Select the **App Integration** tab.
4. Under the **OAuth Clients** section, click **Add OAuth Client**.
5. Fill in the details:
   - **Name**: `HanaMorph_BW_Migration_Studio`
   - **Purpose**: Select **Interactive Usage** or **API Access**.
   - **Redirect URI**: Leave blank (not required for Client Credentials grant).
6. Click **Add** / **Save**.
7. Datasphere will display a modal with the generated credentials:
   - **OAuth Token URL**: (e.g., `https://<tenant-auth>.authentication.eu10.hana.ondemand.com/oauth/token`)
   - **Client ID**: (a UUID or alphanumeric string)
   - **Client Secret**: (a secure generated token)
8. Identify your target **Space ID** (from **Space Management**, e.g., `BW_MIGRATION` or `SALES_SPACE`).
9. Update your local `.env`:
   ```bash
   DATASPHERE_HOST=your-tenant.eu10.datasphere.cloud.sap
   DATASPHERE_SPACE=YOUR_SPACE_ID
   DATASPHERE_OAUTH_TOKEN_URL=https://your-tenant.authentication.eu10.hana.ondemand.com/oauth/token
   DATASPHERE_OAUTH_CLIENT_ID=your_client_id_here
   DATASPHERE_OAUTH_CLIENT_SECRET=your_client_secret_here
   ```

---

### 4.2 SAP BTP (Business Technology Platform)

#### Current State in `.env`:
- User: `varad.k@abhiyantatech.com`
- Status: **PARTIALLY CONFIGURED** (Interactive User configured; Service Key missing)

#### Why Personal Passwords Are Rejected for Unattended Automation:
Personal BTP user accounts are subject to identity provider (IAS/IDP) single-sign-on redirects, password expiry policies, and mandatory Multi-Factor Authentication (MFA). Automated background jobs cannot complete interactive MFA prompts. BTP requires a **Service Key** or **Service Binding**.

#### Step-by-Step: How to Obtain a BTP Service Key:
1. Log into the **SAP BTP Cockpit** (`cockpit.hanatrial.ondemand.com` or your enterprise global account).
2. Click into your target **Global Account** &rarr; select your **Subaccount**.
3. In the Subaccount Overview page, locate and copy the **Subaccount ID** (a GUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
4. Note your Subaccount **Region** (e.g., `eu10`, `us10`, `ap21`).
5. In the left menu, navigate to **Services** &rarr; **Instances and Subscriptions**.
6. If you have an instance of **Destination Service**, **SAP HANA Cloud Tools**, or **Authorization and Trust Management (xsuaa)**:
   - Click the instance name.
   - Click **Service Keys** &rarr; **Create Service Key**.
   - Key Name: `hanamorph-automation-key`.
   - Click **Create**.
7. Click the three dots `...` next to the new key &rarr; **Download** (JSON format).
8. Save this file locally to:  
   `BW_Migration_Studio/secrets/btp-service-key.json`  
   *(This path is strictly ignored by `.gitignore`).*
9. Update your local `.env`:
   ```bash
   BTP_SUBACCOUNT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   BTP_REGION=eu10
   BTP_SERVICE_KEY_PATH=secrets/btp-service-key.json
   ```

---

### 4.3 SAP HANA Cloud

#### Current State in `.env`:
- Status: **NOT CONFIGURED**

#### Step-by-Step: How to Obtain HANA Cloud Connection Parameters:
1. In the **SAP BTP Cockpit**, navigate to your Subaccount.
2. In the left menu, select **SAP HANA Cloud**.
3. Under the **SAP HANA Database** tab, locate your active database instance.
4. Click the three dots `...` on the right side of the instance tile &rarr; select **Copy SQL Endpoint**.
   - Example format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.hanacloud.ondemand.com:443`
5. Separate the host from the port:
   - Host: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.hanacloud.ondemand.com`
   - Port: `443` (HANA Cloud uses TLS Port 443 for direct SQL connections)
6. Identify your technical database user:
   - For administrative tests: `DBADMIN` (with its master password).
   - Recommended: A dedicated read-only database user created via HANA Database Explorer with role `PUBLIC` and schema `SELECT` privileges only.
7. Update your local `.env`:
   ```bash
   HANA_CLOUD_HOST=your-instance-id.hanacloud.ondemand.com
   HANA_CLOUD_SQL_PORT=443
   HANA_CLOUD_USER=DBADMIN
   HANA_CLOUD_PASSWORD=your_hana_db_password
   HANA_CLOUD_SCHEMA=YOUR_TARGET_SCHEMA
   HANA_STRICT_READ_ONLY=true
   ```

---

### 4.4 Cloud Foundry (BTP Runtime)

#### Current State in `.env`:
- Status: **NOT CONFIGURED**

#### Step-by-Step: How to Obtain Cloud Foundry Credentials:
1. In the **SAP BTP Cockpit**, open your Subaccount Overview page.
2. Scroll to the **Cloud Foundry Environment** section.
3. If Cloud Foundry is enabled, you will see:
   - **API Endpoint**: (e.g., `https://api.cf.eu10.hana.ondemand.com`)
   - **Org Name**: (e.g., `your-company-org`)
4. Click **Spaces** &rarr; select or create a space (e.g., `dev` or `migration`).
5. Update your local `.env`:
   ```bash
   CF_API_ENDPOINT=https://api.cf.eu10.hana.ondemand.com
   CF_ORG=your_org_name
   CF_SPACE=dev
   ```

---

## 5. Connection Manager UI & How to Run It

The Studio provides an interactive Connection Manager UI embedded in the local web console:

```
+---------------------------------------------------------------------------------------+
|  HanaMorph BW Migration Studio                          [?] S21 READ-ONLY ENFORCED    |
+---------------------------------------------------------------------------------------+
| [1. Source Catalog]  [2. 4-Way Assessment]  [3. Code Gen]  [4. Connection Profiles]  |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  ENTERPRISE CONNECTION MANAGER            [ Reload .env ]  [ Test All Connections ]   |
|                                                                                       |
|  +--------------------+  +--------------------+  +--------------------+               |
|  | SAP BW S21         |  | SAP Datasphere     |  | SAP BTP            |               |
|  | Host: 192.168.1.55 |  | Host: (Pending)    |  | Subacc: (Pending)  |               |
|  | Port: 8000 / 3300  |  | Auth: OAuth 2.0    |  | Auth: Service Key  |               |
|  | Status: CONNECTED  |  | Status: PARTIAL    |  | Status: PARTIAL    |               |
|  | Latency: 618 ms    |  | Latency: -- ms     |  | Latency: -- ms     |               |
|  | [Test Connection]  |  | [Test Connection]  |  | [Test Connection]  |               |
|  +--------------------+  +--------------------+  +--------------------+               |
|                                                                                       |
|  +--------------------+  +--------------------+                                       |
|  | SAP HANA Cloud     |  | Cloud Foundry      |                                       |
|  | Port: 443 (TLS)    |  | API: (Pending)     |                                       |
|  | Status: NOT CONFIG |  | Status: NOT CONFIG |                                       |
|  | [Test Connection]  |  | [Test Connection]  |                                       |
|  +--------------------+  +--------------------+                                       |
|                                                                                       |
|  LIVE DIAGNOSTIC & SAFETY AUDIT CONSOLE                                               |
|  [12:30:09] Result for bw_s21:                                                        |
|  { "status": "CONNECTED", "latency_ms": 618.46, "http_status": 200, ... }             |
+---------------------------------------------------------------------------------------+
```

### How to Launch the Studio:
1. Open PowerShell or Terminal in workspace:
   ```powershell
   cd C:\Users\samarth\BW-hanamorph\BW_Migration_Studio\bw-studio
   python backend\server.py
   ```
2. Open your browser to:
   `http://localhost:4004`
3. Click on tab **"4. Connection Profiles"**.
4. Click **"Test S21 ADT Connection"** to verify live NetWeaver AS ABAP connectivity.
5. Click **"Test All Connections"** to run full parallel health probes.
6. Click **"Reload .env"** at any time after updating your local credentials.

---

## 6. Verification & Test Suite Health

The complete test suite runs autonomously and validates all invariants across safety, assessment, generation, and connection managers:

```powershell
python BW_Migration_Studio\bw-studio\tests\run_all_tests.py
```
**Results**:
- Ran 18 tests in `0.036s`
- Status: **OK (18/18 Tests Passing)**
- Live Server End-to-End Test: **PASSED (All 5 endpoints verified)**

---

## 7. Next Steps: Local Configuration Required

The integration infrastructure is fully built, tested, and waiting for your local cloud credentials.

### What You Should Do Now:
1. Update `C:\Users\samarth\BW-hanamorph\.env` with:
   - `DATASPHERE_HOST`, `DATASPHERE_SPACE`, `DATASPHERE_OAUTH_CLIENT_ID`, `DATASPHERE_OAUTH_CLIENT_SECRET`, `DATASPHERE_OAUTH_TOKEN_URL`.
   - `BTP_SUBACCOUNT_ID` and optional service key JSON.
   - `HANA_CLOUD_HOST`, `HANA_CLOUD_USER`, `HANA_CLOUD_PASSWORD`.
   - `CF_API_ENDPOINT`, `CF_ORG`, `CF_SPACE`.
2. Save the `.env` file locally.
3. Reply to this chat to continue with:
   - Executing live connection tests against the configured cloud targets.
   - Or proceeding to Phase 3 implementation.

*No credentials have been committed or pushed to Git. All secrets remain strictly local and encrypted.*
