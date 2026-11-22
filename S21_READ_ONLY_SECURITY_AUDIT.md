# HANAMORPH — S21 READ-ONLY SECURITY AUDIT

**Audit Date:** November 22, 2026  
**Security Auditor:** Enterprise Application & SAP Security Auditor  
**Scope:** Complete Code-Level Audit of SAP Integration Paths  
**System Target:** SAP S21 (NetWeaver AS ABAP & BW 7.5, Client 200, User `int_samarth`)  
**Security Compliance Standard:** `AGENTS.md` Zero-Modification & Strict Read-Only Policy  

---

## 1. Threat Model & Context

The SAP administrative user **`int_samarth`** possesses unrestricted privileges (**`SAP_ALL`**) on SAP system S21. In such an environment, any unauthorized write, modify, delete, transport, or activation call could compromise the SAP landscape.

Consequently, HANAMORPH BW Migration Studio enforces a **Defense-in-Depth, Zero-Trust Read-Only Architecture**. Every integration layer must enforce read-only semantics independently, ensuring that no user, API consumer, or automated script can trigger a mutating operation on S21.

---

## 2. Component-by-Component Security Audit

### 2.1 ConnectionHub (`connectors/connection_hub.py`)
- **Role:** Singleton orchestrator for all 5 enterprise target environments (`bw_s21`, `datasphere`, `btp`, `hana_cloud`, `cloud_foundry`).
- **Audit Findings:**
  - Instantiates `BWConnectionManager` passing strictly sanitized configuration from `CredentialVault`.
  - Exposes `test_connection(system_id)` and `get_all_statuses()`.
  - Returns sanitized dictionaries where passwords, secrets, and bearer tokens are masked via `CredentialVault.mask_secret()`.
  - Exposes no proxy methods, command dispatchers, or raw HTTP passthroughs.
- **Verdict:** **SECURE / READ-ONLY ENFORCED**.

### 2.2 BWConnectionManager (`connectors/bw_connection_manager.py`)
- **Role:** Primary communication driver for NetWeaver AS ABAP and ADT endpoints.
- **Audit Findings:**
  1. **HTTP Verb Restriction:**
     ```python
     method_upper = method.upper()
     if method_upper not in ["GET", "HEAD"]:
         raise SecurityViolationError(
             f"[SAFETY GUARDRAIL BLOCKED] Mutating HTTP method '{method_upper}' is forbidden. "
             f"S21 is restricted to strict read-only inspection."
         )
     ```
     *Verification:* Every mutating verb (`POST`, `PUT`, `DELETE`, `PATCH`) is caught and terminated before socket connection or URL construction.
  2. **Forbidden Path Blocklist:**
     ```python
     forbidden_patterns = ["/cts/", "/transports", "/activate", "/lock", "/create", "/delete"]
     if any(p in endpoint.lower() for p in forbidden_patterns):
         raise SecurityViolationError(...)
     ```
     *Verification:* Prohibits any CTS transport requests (`TRKORR`), object activations, locks, or creation endpoints even if submitted via `GET`.
  3. **Credential Sanitization in Exceptions:**
     ```python
     sanitized_err = str(e).replace(self.password, "[REDACTED]") if self.password else str(e)
     raise ConnectionError(f"Network error contacting S21: {sanitized_err}")
     ```
     *Verification:* Network exceptions and HTTP error responses redact passwords to prevent socket error tracebacks from leaking secrets.
- **Verdict:** **SECURE / HARD INVARIANT ACTIVE**.

### 2.3 ADTDiscoveryAdapter (`discovery/adt_discovery_adapter.py`)
- **Role:** Translates high-level discovery requests into ADT search and DDIC inspection calls.
- **Audit Findings:**
  - `search_objects()` dispatches read-only `GET` queries to `/sap/bc/adt/repository/informationsystem/search`.
  - `extract_table_fields()` queries `/source/main` or `/sap/bc/adt/ddic/tables/...` strictly via `GET`.
  - Does not construct, import, or activate DDIC structures.
  - Automatically tags all discovered live objects with `"provenance": "LIVE_VERIFIED"`.
- **Verdict:** **SECURE / READ-ONLY BY DESIGN**.

### 2.4 RFC Integration (`connectors/sap_rfc_connector.py` / `bw_connection_manager.py`)
- **Role:** Gateway for diagnostic RFC calls.
- **Audit Findings:**
  - Implements a strict, immutable whitelist:
    ```python
    APPROVED_BENIGN_RFCS = {"RFC_PING", "STFC_CONNECTION"}
    ```
  - Any RFC invocation outside this whitelist (including `RFC_READ_TABLE`, `BAPI_USER_GET_DETAIL`, CTS functions, or custom function modules) is rejected with `SecurityViolationError`:
    ```python
    if func_upper not in self.APPROVED_BENIGN_RFCS:
        raise SecurityViolationError(
            f"[SAFETY GUARDRAIL BLOCKED] RFC Function '{func_upper}' is forbidden."
        )
    ```
  - Completely prevents RFC table dumps, user privilege manipulation, and background job scheduling.
- **Verdict:** **SECURE / STRICT RFC WHITELIST ACTIVE**.

### 2.5 CredentialVault (`connectors/credential_vault.py`)
- **Role:** Secret storage, environmental loading, and credential encryption.
- **Audit Findings:**
  - Implements AES-256-GCM encryption with PBKDF2 key derivation (100,000 iterations) for local credentials.
  - Generates `.gitignore`-protected `.master_key` and encrypted stores.
  - `mask_secret()` redacts secrets leaving only first and last characters (or full masking for short strings), preventing secret leakage in JSON API responses and logs.
  - File loading asserts strict file access permissions.
- **Verdict:** **SECURE / CIPHER-HARDENED**.

### 2.6 Backend API Endpoints (`backend/server.py`)
- **Role:** HTTP REST API server for the Studio frontend on port 4004.
- **Audit Findings:**
  1. **Zero Raw Proxy Endpoints:** There is no endpoint that accepts arbitrary URLs, methods, or headers to proxy to SAP.
  2. **Endpoint Mapping:**
     - `/api/overview` -> Local SQLite `SELECT count(*)` only.
     - `/api/connections` -> Reads sanitized connection status list.
     - `/api/connections/test` -> Triggers `test_connection()` which performs read-only socket + `/sap/bc/adt/discovery` probe.
     - `/api/discovery/run` -> Runs `DiscoveryEngine`, which executes read-only ADT discovery queries.
     - `/api/assessment/run`, `/api/plans`, `/api/generation/run` -> Perform local Python analytics, CSN generation, and validation against local SQLite.
  3. **Path Traversal & Security Header Defenses:**
     - `do_GET` sanitizes paths, rejecting directory traversal attempts (`..`, `%2f..`).
     - Files such as `.env`, `bw_studio.sqlite`, and source files return `403 Forbidden` / `404 Not Found`.
- **Verdict:** **SECURE / ZERO MUTATION EXPOSURE**.

---

## 3. Server-Side Bypass Analysis

Can an external client bypass read-only restrictions by calling backend endpoints directly?

| Potential Attack Vector | Analysis | Defense Result |
|---|---|---|
| **Direct POST to `/api/discovery/run` with malicious payload** | Payload parameters `systemId` and `liveFilter` are passed to `ADTDiscoveryAdapter.search_objects()`. The adapter only uses `GET` on `/sap/bc/adt/repository/informationsystem/search`. | **BLOCKED:** Even with custom input, the only HTTP method dispatched to S21 is `GET`. |
| **Injecting mutating URL into connection test** | Client sends `{"systemId": "custom_url"}` to `/api/connections/test`. | **BLOCKED:** `ConnectionHub` only looks up registered manager keys (`bw_s21`, `datasphere`, etc.). Unknown keys return `Unknown system ID`. |
| **Tampering with HTTP verb via headers or query strings** | Client sends `X-HTTP-Method-Override: POST` or `?_method=DELETE`. | **BLOCKED:** The studio does not honor method override headers. `BWConnectionManager.execute_sap_http` inspects the hardcoded method parameter and blocks any non-GET/HEAD request. |
| **Calling CTS Transport Endpoints** | Client requests ADT URI containing `/sap/bc/adt/cts/...`. | **BLOCKED:** `BWConnectionManager` actively checks `forbidden_patterns` (`/cts/`, `/transports`, `/activate`, `/lock`) and throws `SecurityViolationError`. |

---

## 4. Audit Conclusion & Compliance Sign-Off

The HANAMORPH BW Migration Studio demonstrates comprehensive read-only safety:
1. **Zero-Modification Policy Compliance:** Fully adheres to `AGENTS.md` and SAP safety guardrails.
2. **Client-Side & Server-Side Enforcement:** Multiple independent layers prevent mutating calls.
3. **Information Disclosure Prevention:** Authentication credentials, cookies, and tokens are protected from memory dumping, logging, and API leakage.

**Final Security Audit Verdict:** **`APPROVED / VERIFIED READ-ONLY`**.
