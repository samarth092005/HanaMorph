# HANAMORPH — Assessment Engine Engineering Guide

## 1. PURPOSE & ARCHITECTURE
The Assessment Engine analyzes discovered canonical metadata objects to evaluate migration readiness, identify technical risks, estimate implementation effort, and determine the optimal modernization target route.

---

## 2. 5-DIMENSION WEIGHTED SCORING MODEL

Every discovered object is evaluated across five weighted dimensions, yielding an aggregate score from 0.0 to 100.0:

1. **Functional Fit (35% Weight)**:
   - Measures semantic alignment with modern analytical architectures.
   - Evaluates dimension modelling, key figure calculations, navigational attributes, and unit conversion support.
2. **Technical Complexity (25% Weight)**:
   - Evaluates custom ABAP routines, AMDP transformations, table joins, compound keys, and custom formulas.
   - Highly complex routines lower the automated conversion score.
3. **Process & Operational Readiness (15% Weight)**:
   - Analyzes delta mechanisms, Process Chain dependencies, execution schedules, and real-time streaming requirements.
4. **Roles & Security Governance (15% Weight)**:
   - Assesses authorization concepts (analysis authorizations `RSECADMIN`), row-level security filters, and data privacy constraints.
5. **Platform Compatibility (10% Weight)**:
   - Assesses compatibility with SAP Datasphere cloud-native engines and SAP HANA Cloud compute.

---

## 3. 4-ROUTE SUITABILITY EVALUATION MATRIX

The engine classifies each object across four modernization destinations:

### 3.1 `native_datasphere`
- **Target**: Pure SAP Datasphere Graphical and SQL Views, Local Tables, and Data Flows.
- **Criteria**: Standard field mappings, simple transformations, standard InfoObjects, moderate volumetry, no proprietary ABAP logic.
- **Benefits**: Zero ABAP runtime footprint, full cloud-native elasticity, direct integration with SAP Analytics Cloud.

### 3.2 `bw_bridge`
- **Target**: SAP Datasphere, BW Bridge (ABAP-based container).
- **Criteria**: Complex ABAP start/end routines, legacy SAP ERP extractor dependencies (ODP-SAPI), delta queue requirements, non-convertible ABAP transformations.
- **Benefits**: Preserves custom extraction logic while enabling data access from modern cloud tools.

### 3.3 `bdc_data_product`
- **Target**: SAP Business Data Cloud (BDC) Data Product.
- **Criteria**: High reusability, certified corporate reporting metrics, clean business semantics, cross-application consumption.
- **Benefits**: Governed, certified corporate analytical contracts with lifecycle management.

### 3.4 `hybrid`
- **Target**: Multi-tier architecture combining BW Bridge staging with Datasphere business modeling.
- **Criteria**: Complex ingestion requiring Bridge paired with modern semantic views requiring Datasphere consumption models.

---

## 4. COMPLEXITY TIERS & RULE ENGINE
The engine evaluates objects against an extensible catalog of assessment rules:
- **LOW COMPLEXITY (Score > 80)**: Direct field mappings, standard InfoObjects, automated 1:1 CSN generation.
- **MEDIUM COMPLEXITY (Score 60 - 80)**: Simple formulas, calculated key figures, basic SQL view translation.
- **COMPLEX (Score 40 - 59)**: ABAP routines requiring SQL / Python conversion, multi-table joins.
- **HIGHLY COMPLEX (Score < 40)**: Custom AMDP scripts, complex legacy ABAP routines, circular chain dependencies.
