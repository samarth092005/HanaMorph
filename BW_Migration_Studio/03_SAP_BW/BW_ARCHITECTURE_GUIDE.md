# SAP BW & BW/4HANA Architecture & Migration Guide

## 1. Classical BW vs BW on HANA vs BW/4HANA
- **Classical BW (NetWeaver 7.x)**: Uses InfoCubes, MultiProviders, classic DSOs, and persistent PSA staging tables. Data transformation executed via ABAP routines on the application server.
- **BW on HANA (BW 7.5)**: Introduces Advanced DataStore Objects (ADSOs) and CompositeProviders. Transformations pushed down to the HANA database layer via HANA Execution (SAP HANA Analysis Processes / AMDP).
- **BW/4HANA**: Replaces all legacy objects strictly with ADSOs, CompositeProviders, and Open ODS Views. Removes PSA and classical InfoCubes completely.

## 2. Ingestion & Transformation Mechanics
- **Operational Data Provisioning (ODP)**: Bypasses the traditional PSA layer by reading directly from Operational Delta Queues (ODQ).
- **Data Transfer Process (DTP)**: Governs package sizing, semantic partitioning, and delta extraction modes.
- **Transformations**: Composed of rule groups, direct field assignments, formulas, master data reads, and procedural ABAP routines (Start, End, Field, and Expert).
