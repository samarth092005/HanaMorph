# M4.5B — SAC ANALYTICAL MODEL SEMANTICS REMEDIATION & VERIFICATION AUDIT

**Project:** HANAMORPH — SAP BW Migration & Modernization Studio  
**Workstream:** Workstream B — SAC Model Generator Semantic Classification  
**Scope:** SAC Analytical Model Generator, Field Classification Taxonomy, and Ambiguity Annotations  
**Application Root:** `BW_Migration_Studio\bw-studio`  
**Status:** `VERIFIED_FIXED`  
**Date:** November 22, 2026  

---

## 1. Scope and Objective
Remediate field semantic classification flaws in `generation_engine/sac_model_generator.py`:
- **GAP-05:** Naive type-based heuristic classifying all numeric/DEC fields as Measures (e.g., `CUSTOMER_ID`, `DOCUMENT_NUMBER`, `POSTAL_CODE`, `FISCPER`), leading to invalid SAC Analytical Model definitions.
- Establish a strict 5-tier semantic classification priority order.
- Prevent non-additive identifier fields from misclassifying as Measures.
- Introduce `ambiguous_fields` metadata and `review_required` flags with diagnostic rationales for unresolved fields.

---

## 2. Files Inspected and Changed

| File Path | Role | Change Description |
| :--- | :--- | :--- |
| `generation_engine/sac_model_generator.py` | Generation Engine | Replaced naive `data_type in ["DEC", "CURR", "QUAN", "INT", "FLTP"]` measure check with priority-ordered 5-tier `_classify_field_semantics` method. Added `ambiguous_fields` and `review_required` properties to model specification. |
| `tests/test_m4_5_remediation.py` | Test Suite | Added dedicated tests `test_b1` through `test_b4` validating explicit role overrides, numeric identifier protection, measure detection, and ambiguity annotations. |

---

## 3. Root Cause and Implementation Details

### 3.1. GAP-05: Naive Numeric Measure Classification
- **Root Cause:** The previous implementation inspected only `field.get("data_type")`. If the data type was `DEC`, `CURR`, `QUAN`, `INT`, or `FLTP`, it was unconditionally mapped into `measures` with default aggregation `SUM`. In enterprise SAP BW/ERP systems, many dimensions are numeric (e.g., decimal customer codes `KUNNR`, fiscal periods `FISCPER`, document items `POSNR`, postal codes `PSTLZ`).
- **Fix:** Implemented a priority-ordered 5-tier semantic classifier:
  1. **Tier 1 (Explicit Analytics):** Checks for explicit `role == "MEASURE"` or `role == "DIMENSION"` or explicit `aggregation_type`.
  2. **Tier 2 (Aggregation Mapping):** If `aggregation_type` is non-empty (`SUM`, `AVG`, `COUNT`, `MAX`, `MIN`), classifies as Measure.
  3. **Tier 3 (Field-Role Metadata):** Respects upstream schema mapping role hints.
  4. **Tier 4 (Business Identifier & Semantic Patterns):** Pattern matching to distinguish Identifiers from Measures:
     - *Dimension Indicators:* Names ending with `_ID`, `_NO`, `_NR`, `_NUM`, `_CODE`, `_CD`, `_TYPE`, `_KEY`, `_FLAG`, `_STATUS`, `_IND`, or specific BW names (`FISCPER`, `CALMONTH`, `CALYEAR`, `POSTAL_CODE`, `ZIP`). Classified as Dimension even if numeric/DEC.
     - *Measure Indicators:* Names ending with `_AMT`, `_AMOUNT`, `_QTY`, `_QUANTITY`, `_VOL`, `_VOLUME`, `_RATE`, `_PCT`, `_PRICE`, `_COST`, `_REV`, `_REVENUE`, `_BAL`, `_BALANCE`, or SAP types `CURR`, `QUAN`. Classified as Measure.
  5. **Tier 5 (Ambiguity Flagging):** For numeric fields with no matching pattern and no explicit metadata, defaults safely to Dimension, but flags `review_required: true`, adds `review_reason`, and records the field into `spec["ambiguous_fields"]`.

---

## 4. Test Verification & Commands

### Test Execution Command
```powershell
cd BW_Migration_Studio\bw-studio
python -m unittest tests.test_m4_5_remediation.TestM45WorkstreamB_SACSemantics
```

### Actual Test Results
```text
....
----------------------------------------------------------------------
Ran 4 tests in 0.008s

OK
```

All 4 test cases passed:
1. `test_b1_explicit_analytical_semantics_priority`: Verified Tier 1 explicit role override takes absolute precedence over data type.
2. `test_b2_numeric_dimensions_not_misclassified_as_measures`: Verified `CUSTOMER_ID` (DEC), `DOCUMENT_NUMBER` (INT), `POSTAL_CODE` (DEC), and `FISCPER` (NUMC) are correctly routed to `dimensions`.
3. `test_b3_numeric_measures_correctly_classified`: Verified `NET_AMOUNT`, `QUANTITY`, and `REVENUE` are routed to `measures`.
4. `test_b4_ambiguous_fields_flagged_with_review_required`: Verified `CUSTOM_METRIC_01` (DEC without clear suffix) is categorized as Dimension with `review_required: true` and documented in `ambiguous_fields`.

---

## 5. Known Limitations & Outstanding Risks
- Highly unusual custom abbreviation patterns (e.g., `ZVALX` with no type hint) will trigger Tier 5 ambiguity review. This is by design to ensure human data architects review edge cases rather than creating erroneous aggregations in SAC.

---

## 6. Final Verdict
**`VERIFIED_FIXED`**  
The SAC model generation semantic engine strictly obeys 5-tier classification rules, completely preventing identifier misclassification as measures while tracking ambiguous fields.
