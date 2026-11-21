# SAP Datasphere Modeling & Modernization Architecture

## 1. Core Modeling Hierarchy
SAP Datasphere replaces monolithic BW InfoProviders with decoupled, modular data artifacts:
1. **Spaces**: Dedicated virtual containers allocating in-memory and disk compute.
2. **Data Builder**:
   - **Local Tables**: Persisted tables residing natively in HANA Cloud storage.
   - **Remote Tables**: Federated virtual tables querying remote systems (e.g. S/4HANA, SAP BW) without data persistence.
   - **Graphical Views / SQL Views**: Declarative transformations supporting projections, joins, unions, and aggregations.
   - **Transformation Flows**: Native push-down ELT operations loading data from source tables into target tables.
3. **Analytic Models**:
   - The primary consumption layer for reporting (replaces BW Queries and Analytic Datasets).
   - Star join schema binding central Fact Views with peripheral Dimension Views.
   - Defines restricted measures, calculated measures, hierarchies, and variables.
