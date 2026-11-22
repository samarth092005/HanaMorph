# BW MIGRATION STUDIO — SECURITY & READ-ONLY AUDIT
**Standard:** Enterprise SAP Safety Guardrail & Threat Model Verification  
**Enforcement Directive:** `AGENTS.md` (Strict Read-Only Enforcement)  
**Status:** **AUDITED & VERIFIED (READ-ONLY INVARIANT CERTIFIED)**  

---

## 1. SAP S21 Read-Only Invariant Enforcement

Because the SAP service account `int_samarth` possesses administrative privileges (`SAP_ALL`) on system `S21`, client-side security guardrails are non-negotiable.

### 1.1 HTTP Method Whitelist
In `connectors/bw_connection_manager.py` (lines 39-44):
```python
method_upper = method.upper()
if method_upper not in ["GET", "HEAD"]:
    raise SecurityViolationError(
        f"[SAFETY GUARDRAIL BLOCKED] Mutating HTTP method '{method_upper}' is forbidden. "
        f"S21 is restricted to strict read-only inspection."
    )
```
- **Verification Evidence:** `test_http_mutating_verbs_strictly_blocked` in `tests/test_m1_connectivity_security.py` executes `POST`, `PUT`, `DELETE`, and `PATCH`. All four calls raise `SecurityViolationError` synchronously before socket creation.
- **Live S21 Test Evidence:** `tests/test_live_s21_verification.py` confirms that mutating calls are blocked against the live endpoint.

### 1.2 Prohibited Endpoint Patterns
In `connectors/bw_connection_manager.py` (lines 46-50):
```python
forbidden_patterns = ["/cts/", "/transports", "/activate", "/lock", "/create", "/delete"]
if any(p in endpoint.lower() for p in forbidden_patterns):
    raise SecurityViolationError(
        f"[SAFETY GUARDRAIL BLOCKED] Endpoint '{endpoint}' is prohibited by zero-modification policy."
    )
```

### 1.3 RFC Diagnostic Allowlist
In `connectors/bw_connection_manager.py` (lines 104-108):
```python
APPROVED_BENIGN_RFCS = {"RFC_PING", "STFC_CONNECTION"}
if func_upper not in self.APPROVED_BENIGN_RFCS:
    raise SecurityViolationError(
        f"[SAFETY GUARDRAIL BLOCKED] RFC Function '{func_upper}' is forbidden."
    )
```
- RFC execution is restricted to benign ping functions. Any attempt to invoke `RFC_READ_TABLE`, `BAPI_*`, or CTS functions is immediately aborted.

---

## 2. Credential Encryption & Masking

1. **At-Rest Encryption:** Handled via `CredentialVault` (`connectors/credential_vault.py`) utilizing `cryptography.fernet.Fernet` (AES-128-CBC with PKCS7 padding and HMAC-SHA256).
2. **Master Key Protection:** The master key is stored in `BW_Migration_Studio/.master_key` which is explicitly ignored by `.gitignore`.
3. **Log Sanitization:** `bw_connection_manager.py` sanitizes error strings via `.replace(self.password, "[REDACTED]")`. `CredentialVault.mask_secret()` replaces sensitive strings with masked asterisks.
4. **Zero Passwords in Code:** Git status confirms `.env` is untracked and gitignored.

---

## 3. Web & API Security Findings

### Finding SEC-01: Unauthenticated REST Endpoints
- **Severity:** Medium (Local Development) / High (Production Network Deployment).
- **Description:** `backend/server.py` does not authenticate incoming HTTP requests on port 4004. Any client on the local host can trigger discovery, generate plans, or execute connection tests.
- **Remediation:** Introduce an API token header (`Authorization: Bearer <token>`) validated against an environment secret `STUDIO_API_TOKEN`.

### Finding SEC-02: Path Traversal Protection Verified
- **Severity:** Low (Mitigated).
- **Description:** Static file serving in `server.py:55` checks for `..`, `\`, `%2f`, and verifies that canonical target paths stay within `FRONTEND_DIR`.
- **Verification Evidence:** `test_06_traversal_blocked` in `tests/test_server_live.py` passes all attack vectors.
