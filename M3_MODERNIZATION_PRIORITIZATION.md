# HANAMORPH — M3 MODERNIZATION PRIORITIZATION & WAVES
**Module:** `assessment_engine/prioritization_engine.py`  
**Sequencing Strategy:** Topological Sort + Multi-Factor Cohort Ranking  
**Status:** **VERIFIED**  

---

## 1. Prioritization Cohorts

Assessed objects are classified into 6 discrete cohorts:

1. **`QUICK_WINS`**: Low complexity ($<45$), low risk ($<35$), expected hours $<18$h. Immediate deployment candidates providing rapid ROI.
2. **`HIGH_VALUE`**: Foundational providers with high fan-out ($>2$ downstream models). Staged early to unblock analytics.
3. **`STANDARD`**: Standard operational ADSOs and transactional data stores.
4. **`HIGH_RISK`**: Complex routines or high volume requiring senior architectural review.
5. **`REDESIGN_REQUIRED`**: Architectural restructuring required prior to staging.
6. **`BLOCKED`**: Missing upstream dependencies or unsupported platform constructs.

---

## 2. 4-Wave Migration Roadmap

The migration waves respect strict topological precedence: no object is scheduled in a wave before its prerequisite sources.

```
+--------------------------------------------------------------------------------+
|                         MIGRATION WAVE ROADMAP                                 |
+--------------------------------------------------------------------------------+

  [ WAVE 1: FOUNDATIONAL STAGING & QUICK WINS ]
  * /BIC/AZSAM_PR011 (Inbound Table)
  * /BIC/AZSAM_PR012 (Active Data Table)
  * ZSAM_SO_IA       (Sales InfoArea)
  * /BIC/AZSAM_SO011 (Inbound Table)
  -------------------------------------------------------------------------------
  [ WAVE 2: CORE PERSISTENCE & DATASTORE LAYERS ]
  * ZSAM_SO01        (Sales Order DataStore)
  * ZSAM_PR01        (Purchase Requisition DataStore)
  * /BIC/AZSAM_PR016 (Extraction View)
  -------------------------------------------------------------------------------
  [ WAVE 3: SEMANTIC COMPOSITE LAYERS & ANALYTICS ]
  * ZSAM_SO_CP       (Sales Order CompositeProvider)
  * ZCP_EKPO         (Purchase Requisition CompositeProvider)
  * ZBW_Q001         (Purchase Analytics Query)
  -------------------------------------------------------------------------------
  [ WAVE 4: REMEDIATION & HIGH-RISK STAGING ]
  * ZSAM_FI_ROUTINE  (Complex Routine Staging in SAP BW Bridge)
```
