# HANAMORPH — M3 REMAINING GAPS AND BLOCKERS
**Status Assessment:** Operational & Architectural Review  
**Milestone Transition:** M3 Closure -> M4 Preparation  

---

## 1. Identified Operational Gaps & Workarounds

| # | Item / Limitation | Root Cause | Impact | Verified Mitigation / Workaround |
| :- | :--- | :--- | :--- | :--- |
| 1 | **Proprietary BWMT ADT Endpoints Return 404** | NetWeaver AS ABAP 7.53 does not install BW Modeling Tools REST ICF nodes (`/sap/bc/adt/bw/*`) | Live extraction cannot parse CompositeProvider join trees directly via HTTP | Semantic structures are ingested from Eclipse BWMT workspace cache (`.bw/` XML files) via `IngestionEngine`. |
| 2 | **SAP S21 Account Has `SAP_ALL`** | User `int_samarth` holds unrestricted privileges in S21 Client 200 | Write or transport calls could compromise system integrity | Client-side strict read-only gatekeeper hardcoded in `BWConnectionManager.execute_sap_http` blocks all non-GET/HEAD methods. |
| 3 | **BTP User/Password Blocked for Automation** | SAP BTP policy blocks interactive basic authentication for automated CLI tools | Direct username/password authentication fails | BTP integration must strictly consume Service Key bindings (`VCAP_SERVICES`) with client credentials. |
| 4 | **Datasphere Space Provisioning** | Target Datasphere space `SALES_ANALYTICS` must be pre-created by tenant administrator | CLI deployment fails if space does not exist | Pre-deployment verification step checks space existence via `@sap/datasphere-cli`. |

---

## 2. Blockers for Subsequent Milestones

- **Milestone M4:** **ZERO BLOCKERS.** The metadata repository, 7-level validation engine, and CSN/DDL code generation baseline are fully operational.
