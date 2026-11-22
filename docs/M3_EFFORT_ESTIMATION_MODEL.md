# HANAMORPH — M3 EFFORT ESTIMATION MODEL
**Module:** `assessment_engine/effort_estimation_engine.py`  
**Estimation Mode:** Explainable Low, Expected, and High Person-Hours  
**Status:** **IMPLEMENTED & VERIFIED**  

---

## 1. Estimation Methodology

The Migration Effort Estimation Model computes person-hours required for end-to-end modernization based on:
1. **Base Architectural Effort** by object type (ADSO: 12h, HCPR: 16h, Query: 14h, Table: 8h).
2. **Transformation Refactoring Multiplier** (Standard mapping: 1.0x; Custom ABAP routines: 2.5x – 3.5x).
3. **Dependency & Integration Effort** (+2.0h per upstream source; +1.5h per downstream consumer).
4. **Validation & Testing Effort** (+4.0h baseline testing + data reconciliation).

### Uncertainty Ranges:
- **Low (P25):** $-20\%$ from expected effort (smooth automation, zero schema adjustments).
- **Expected (P50):** Baseline calibrated person-hours.
- **High (P90):** $+20\%$ to $+45\%$ above expected effort (accounting for risk score and manual validation).

---

## 2. Portfolio Effort Summary (S21 Baseline)

$$	ext{Total Expected Effort} = 178.0 	ext{ person-hours}$$
$$	ext{Effort Range} = [118.0	ext{h Low} \quad 	ext{to} \quad 272.0	ext{h High}]$$

### Breakdown by Work Phase:
- **Core Schema & Model Generation:** 45 person-hours (Automated via HANAMORPH generators)
- **Transformation & Logic Refactoring:** 48 person-hours
- **Lineage Wiring & Dependency Integration:** 35 person-hours
- **Data Reconciliation, Testing & Certification:** 50 person-hours
