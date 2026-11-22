# HANAMORPH — SAP BW Connection and Security Guide

## 1. PURPOSE & OVERVIEW
This guide provides complete instructions for configuring, establishing, and validating read-only connectivity to SAP BW 7.50, BW/4HANA, S21, and S/4HANA systems from HANAMORPH BW Migration Studio.

## 2. STRICT READ-ONLY SAFETY MANDATE
In accordance with `AGENTS.md` and enterprise safety guardrails:
- The connector executes **strictly non-mutating HTTP requests** (`GET`, `HEAD`).
- Mutating HTTP methods (`POST`, `PUT`, `DELETE`, `PATCH`) are jailed and rejected at the connector layer.
- Administrative endpoints (`/transports/`, `/cts/`, `/activate`, `/lock`, `/workbench/`) are blocked.
- RFC diagnostics are whitelisted to `RFC_PING` and `STFC_CONNECTION` only.

## 3. CONFIGURATION PARAMETERS (`.env`)
```bash
# SAP BW System S21 Configuration
BW_SYSTEM_ID=S21
BW_HOST=10.0.0.50
BW_INSTANCE=00
BW_CLIENT=200
BW_USER=int_samarth
BW_PASSWORD=****************
BW_AUTH_METHOD=BASIC
BW_USE_HTTPS=false
BW_TIMEOUT_SEC=15
```

## 4. CONNECTION VALIDATION WORKFLOW
1. Open HanaMorph UI at `http://localhost:4004`.
2. Navigate to **Connections** tab.
3. Click **Test S21 Connection** to verify network connectivity, NetWeaver HTTP reachability, and benign RFC diagnostics.
4. If connection is successful, status shows **CONNECTED** with measured latency in milliseconds.
5. All credentials are masked in logs and diagnostic outputs (`***MASKED***`).
