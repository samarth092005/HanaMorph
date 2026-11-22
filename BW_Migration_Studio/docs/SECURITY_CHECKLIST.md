# HANAMORPH — Enterprise Security Checklist & Verification

## 1. PURPOSE & MANDATE
This checklist establishes the non-negotiable security requirements, verification tests, and operational guardrails for running HANAMORPH in enterprise SAP landscapes.

---

## 2. SECURITY VERIFICATION CHECKLIST

| Check ID | Security Domain | Verification Standard | Status | Enforcement Mechanism |
|---|---|---|---|---|
| `SEC-01` | SAP System Protection | Zero repository modifications, DDIC changes, or locks on SAP S21 | **VERIFIED** | Non-mutating HTTP verb jail in `BWConnectionManager`. Mutating verbs (`POST`, `PUT`, `DELETE`) raise `SAPSecurityViolationError`. |
| `SEC-02` | RFC Hardening | Strictly limit RFC function module invocations | **VERIFIED** | Whitelist in RFC connector allowing only `RFC_PING` and `STFC_CONNECTION`. All other function modules are rejected before dispatch. |
| `SEC-03` | Credential Redaction | No cleartext passwords, OAuth secrets, or tokens in logs or UI | **VERIFIED** | Regex sanitizer in `logging_config.py` and JSON serializer masking credentials as `***MASKED***`. |
| `SEC-04` | SQL Injection Prevention | All SQLite database operations use parameterized statements | **VERIFIED** | 100% parameterization (`?` placeholders) across all engines; zero string formatting in SQL executions. |
| `SEC-05` | Path Traversal Defense | Secure file downloads and package extraction | **VERIFIED** | Path validation and sanitization using `os.path.abspath` and boundary checking against `delivery/` and `output/`. |
| `SEC-06` | Human-in-the-Loop Gate | No code generation without explicit plan approval | **VERIFIED** | `generation_engine.py` asserts `plan.status == 'APPROVED'`; unapproved requests are blocked with HTTP 403. |
| `SEC-07` | Local Workspace Boundary | Generated artifacts must never be remotely deployed automatically | **VERIFIED** | Artifacts are strictly emitted to local workspace directories (`output/`, `delivery/`). No remote push scripts are triggered. |
| `SEC-08` | Denial-of-Service Defense | Bounded write queue and backpressure handling | **VERIFIED** | `SingleWriterQueue` enforces capacity limits (1000 items) and raises `QueueFull` on backpressure rather than consuming infinite memory. |

---

## 3. AUDIT REPRODUCTION COMMANDS
Verify security controls locally using the automated test suite:
```powershell
# Run security test fixtures
python tests\run_all_tests.py
```
Expected output:
- `TestBWConnectionManager.test_mutating_http_blocked` -> PASS
- `TestBWConnectionManager.test_disallowed_rfc_blocked` -> PASS
- `TestLogging.test_credential_masking` -> PASS
- `TestGenerationEngine.test_unapproved_plan_rejected` -> PASS
