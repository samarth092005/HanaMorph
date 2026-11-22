# HANAMORPH — M3 COMPLEXITY ENGINE DESIGN
**Module:** `assessment_engine/complexity_engine.py`  
**Architecture:** 7-Dimensional Object Complexity Scoring  
**Status:** **IMPLEMENTED & VERIFIED**  

---

## 1. Engine Purpose & Overview

The Object Complexity Engine evaluates the technical and architectural difficulty of migrating an SAP BW object to SAP Datasphere and HANA Cloud. It replaces simplistic field-count heuristics with a rigorous 7-dimensional scoring model based strictly on verified repository metadata.

---

## 2. The 7 Complexity Dimensions

Each dimension is scored from 0 (trivial) to 100 (maximum complexity) and assigned an enterprise weight:

| Dimension | Weight | Primary Factors Measured | Scoring Logic |
| :--- | :--- | :--- | :--- |
| **1. Structural** | **20%** | Column count, key count, field width | 50+ fields = 60; 100+ fields = 90; wide records add complexity |
| **2. Dependency** | **20%** | Fan-in (sources) & Fan-out (consumers) | High fan-out increases blast radius; multiple hops add coupling |
| **3. Transformation** | **20%** | ABAP routines, rule groups, start/end routines | Custom ABAP = 85-95; 1:1 direct pass-through = 10 |
| **4. Data Model** | **15%** | Join multiplicity, union depth, aggregation | Joins/Unions in CompositeProviders = 45-75; flat ADSO = 15 |
| **5. Semantic** | **10%** | Hierarchies, currencies, units, languages | Currency fields (`CURR`/`CUKY`) = +15; units (`QUAN`/`UNIT`) = +10 |
| **6. Customization** | **10%** | User exits, customer includes, modification flag | Custom namespaces (`Z*`, `Y*`) and includes score higher |
| **7. Operational** | **5%** | Data volume, delta latency, SLA criticality | High-frequency delta staging increases operational risk |

---

## 3. Overall Complexity Calculation

The overall complexity score is the weighted sum of all 7 dimensions:

$$	ext{Overall Score} = \sum_{i=1}^{7} (D_i 	imes W_i)$$

### Categorization Thresholds:
- **`LOW` (0 – 35):** Simple tabular structures, 1:1 mappings, standard data types. Suitable for automated migration.
- **`MEDIUM` (36 – 60):** Standard ADSOs with currency/unit references or simple join CompositeProviders.
- **`HIGH` (61 – 80):** Multi-table join/union models, extensive field catalogs, or dependencies with routines.
- **`VERY_HIGH` (81 – 100):** Procedural ABAP transformations, complex BEx customer-exit variables, cyclic dependencies.
