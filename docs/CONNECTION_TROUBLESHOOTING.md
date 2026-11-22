# HANAMORPH — Connection Troubleshooting and Diagnostic Guide

## 1. OVERVIEW
This guide outlines troubleshooting steps, root-cause analyses, error code references, and remediation workflows for connection failures across SAP BW (S21, BW 7.5, BW/4HANA), SAP Datasphere, and SAP BTP.

---

## 2. COMMON CONNECTION ERRORS & RESOLUTION MATRIX

| Error Code / Symptom | Probable Cause | Diagnostic Command / Inspection | Resolution Workflow |
|---|---|---|---|
| `ERR_BW_REFUSED` (Port 8000 / 3300) | NetWeaver ICM HTTP service is inactive or host is unreachable | `Test-NetConnection -ComputerName $BW_HOST -Port 8000` | Verify NetWeaver ICM is active (`SMICM`), verify host routing and firewall rules. |
| `ERR_AUTH_BASIC_FAILED` (HTTP 401) | Invalid credentials, locked user, or incorrect client number | Verify Client (e.g. 200) and `BW_USER` | Confirm `int_samarth` account is unlocked (`SU01`), verify password and client number in `.env`. |
| `ERR_MUTATING_VERB_BLOCKED` | Attempted non-GET HTTP call on S21 | Check backend logs for HTTP verb jail violation | Enforce read-only `GET`/`HEAD`. HANAMORPH strictly prohibits mutating methods against S21. |
| `ERR_RFC_NOT_WHITELISTED` | Disallowed RFC function module invocation | Check backend RFC dispatcher log | Only `RFC_PING` and `STFC_CONNECTION` are permitted for diagnostics. |
| `ERR_OAUTH_TOKEN_FAILED` (Datasphere) | Invalid OAuth Client ID / Secret or wrong token URL | `curl -X POST -u "$CLIENT_ID:$SECRET" $TOKEN_URL -d "grant_type=client_credentials"` | Re-issue OAuth client secret in Datasphere System Administration. Check token URL region. |
| `ERR_DATASPHERE_SPACE_404` | Space does not exist or user lacks space access | Check Datasphere Space Management | Confirm the space name matches `DATASPHERE_SPACE` exactly (case-sensitive) and OAuth client has space permissions. |
| `ERR_BTP_DEST_NOT_FOUND` | Destination name does not exist in subaccount | Check BTP Cockpit > Connectivity > Destinations | Verify `BTP_TARGET_DESTINATION_NAME` matches configured destination in BTP cockpit. |
| `ERR_TIMEOUT` (15s exceeded) | High latency link, WAN packet drop, or proxy delay | `ping -n 4 $BW_HOST` | Increase `BW_TIMEOUT_SEC` in `.env` (e.g., from 15 to 30) or verify VPN/Cloud Connector tunnel. |

---

## 3. STEP-BY-STEP DIAGNOSTIC PROCEDURES

### 3.1 Validating SAP BW HTTP Endpoint Manually (PowerShell)
To verify ICM HTTP reachability without modifying anything:
```powershell
$uri = "http://10.0.0.50:8000/sap/public/ping"
try {
    $res = Invoke-WebRequest -Uri $uri -Method GET -TimeoutSec 10 -UseBasicParsing
    Write-Output "Status: $($res.StatusCode)"
} catch {
    Write-Output "ICM Ping Error: $_"
}
```

### 3.2 Validating SAP Datasphere OAuth Handshake (PowerShell)
```powershell
$tokenUrl = "https://subaccount.authentication.eu10.hana.ondemand.com/oauth/token"
$body = @{
    grant_type = "client_credentials"
    client_id = "sb-datasphere!b123"
    client_secret = "your_secret"
}
try {
    $tokenRes = Invoke-RestMethod -Uri $tokenUrl -Method Post -Body $body
    Write-Output "Token acquired successfully. Expires in: $($tokenRes.expires_in)s"
} catch {
    Write-Output "Datasphere OAuth Failed: $_"
}
```

---

## 4. SECURITY LOGGING AND AUDIT TRAIL
- All failed connection attempts are logged into `BW_Migration_Studio/bw-studio/logs/connection_audit.log`.
- Log entries include timestamp, remote IP, system type, HTTP response code, and latency.
- Credentials and tokens are automatically masked by `ConnectionManager` using the regex pattern:
  `(?i)(password|secret|token)=[^&\s]+` -> `$1=***MASKED***`.
