# HANAMORPH — Milestone M4 Target Architecture & Design Report
## 4-Route Target Architecture Modeling & Semantic Mapping Engine

---

### DOCUMENT CONTROL
- **Document ID**: `HANAMORPH-M4-ARCHITECTURE-REPORT`
- **Milestone Target**: Milestone M4 (Target Architecture and Modernization Design)
- **Target Repository**: `BW_Migration_Studio/bw-studio`
- **Date**: November 2026
- **Status**: **VERIFIED & IMPLEMENTED**

---

## 1. TARGET ARCHITECTURE MATRIX

Milestone M4 establishes formal mapping rules translating legacy SAP BW concepts into target modern representations across four target routes:

| SAP BW Source Concept | Native Datasphere Target | SAP BW Bridge Target | BDC Target | Hybrid Architecture |
| :--- | :--- | :--- | :--- | :--- |
| **DataSource (OSRC)** | Replication Flow / Ingestion | Inbound Remote Source | Ingestion Connector | Bridge Replication Flow |
| **InfoObject (IOBJ)** | Dimension Entity / Attribute | BW Bridge InfoObject | Semantic Attribute | Shared Dimension Entity |
| **ADSO (Standard)** | Local Table (Column Store) | BW Bridge ADSO | Data Product Entity | Bridge Ingestion Table |
| **ADSO (Staging)** | Inbound Local Table | Staging ADSO | Raw Storage Entity | Inbound Staging Table |
| **Transformation (TRFN)**| Graphical View / Calculated Cols | ABAP Transformation | Transformation Pipeline | Bridge Transformation |
| **DTP (Data Transfer Process)**| Replication / Data Flow | BW Bridge DTP | Orchestrated Pipeline | Bridge Execution |
| **CompositeProvider (HCPR)**| Graphical View (Star / Join) | Virtual Provider | Analytical View | Datasphere Graphical View |
| **BW Query (ELEM)** | Analytic Model / SAC Story | Analytic Model View | Consumption Product | Datasphere Analytic Model |
| **Process Chain (RSPC)** | Task Chain / Orchestrator | BW Bridge Process Chain | Cloud Orchestration | Task Chain Trigger |

---

## 2. TOPOLOGICAL SEQUENCING & CYCLE RESOLUTION

- Planning engine uses Tarjan's SCC cycle detection.
- Soft reporting feedback loops are decoupled for linear topological execution.
- Hard mutual ETL cycles are flagged for manual architect redesign before approval.
- Plans require explicit approval (`status = 'APPROVED'`) before code generation is unlocked.

---

## 3. VERIFICATION EVIDENCE

- Automated tests `test_acyclic_graph_topological_sort`, `test_type_2_lookup_induced_cycle_decoupling`, and `test_type_3_mutual_hard_etl_cycle_flags_redesign` in `test_m1_dependency_cycle.py` PASSED (100%).
- Full project creation, DAG sequencing, and human approval gates verified in `test_end_to_end_engines.py`.
