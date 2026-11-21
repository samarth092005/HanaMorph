# SAP Datasphere BW Bridge Architecture & Evaluation

## 1. Role of BW Bridge
SAP Datasphere BW Bridge provides an ABAP-based cloud runtime on SAP BTP specifically designed to preserve existing SAP BW investments (such as complex extractors, ABAP transformations, and classical DataSources).

## 2. Conversion Routes
- **Shell Conversion**: Converts metadata models (ADSOs, CompositeProviders) into BW Bridge objects without migrating historical data.
- **Remote Conversion**: Migrates both metadata and historical data over RFC / Cloud Connector connections.
- **Recommendation for HanaMorph**: For standard models (e.g. `ZSAM_SO01`), native Datasphere modernization is preferred to eliminate ABAP runtime overhead. BW Bridge is reserved for models containing irreplaceable custom ABAP routines.
