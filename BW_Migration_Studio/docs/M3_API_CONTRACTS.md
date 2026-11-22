# HANAMORPH — M3 API CONTRACTS SPECIFICATION
**Version:** 3.0.0  
**Transport:** HTTP / JSON  
**Base URL:** `http://localhost:8000/api/intelligence/`  
**Status:** **IMPLEMENTED & AUDITED**  

---

## 1. Endpoint: `GET /api/intelligence/landscape`

Returns real-time aggregate portfolio metrics computed deterministically from SQLite.

### Response `200 OK`:
```json
{
  "total_objects": 11,
  "mean_complexity": 28.4,
  "total_effort_expected": 178.0,
  "high_risk_count": 0,
  "critical_risk_count": 0,
  "datasphere_fit_rate": 73,
  "by_type": {
    "ADSO": 2,
    "COMPOSITE_PROVIDER": 2,
    "TABL": 4,
    "VIEW": 2,
    "INFOAREA": 1
  },
  "by_complexity": {
    "LOW": 9,
    "MEDIUM": 2,
    "HIGH": 0,
    "VERY_HIGH": 0
  },
  "by_risk": {
    "LOW": 9,
    "MEDIUM": 2,
    "HIGH": 0,
    "CRITICAL": 0
  },
  "by_route": {
    "Native Datasphere": 8,
    "SAP BW Bridge": 2,
    "BDC Data Product": 1
  }
}
```

---

## 2. Endpoint: `GET /api/intelligence/prioritization`

Returns categorized cohorts and the topologically ordered migration wave sequence.

### Response `200 OK`:
```json
{
  "cohorts": {
    "quick_wins": ["ZSAM_SO_IA", "/BIC/AZSAM_PR011"],
    "high_value_candidates": ["ZSAM_SO01", "ZSAM_PR01"],
    "standard_migration": ["ZSAM_SO_CP", "ZBW_Q001"],
    "high_risk_candidates": [],
    "redesign_required": [],
    "blocked": []
  },
  "waves": {
    "wave_1": [...],
    "wave_2": [...],
    "wave_3": [...],
    "wave_4": [...]
  }
}
```

---

## 3. Endpoint: `GET /api/intelligence/object?objectName={name}`

Returns comprehensive technical dossier, 7D complexity breakdown, 4 route evaluations, risk profile, and effort estimates.

---

## 4. Endpoint: `GET /api/intelligence/lineage?objectName={name}`

Returns multi-hop upstream predecessors, downstream consumers, missing dependencies, and blast radius impact.

---

## 5. Endpoint: `POST /api/intelligence/assess`

Triggers full re-evaluation of all catalog objects across all 7 intelligence engines and updates SQLite database tables.
