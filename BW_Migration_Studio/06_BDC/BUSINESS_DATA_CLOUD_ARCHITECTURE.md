# SAP Business Data Cloud (BDC) Architecture

## 1. BDC Ecosystem Overview
The SAP Business Data Cloud (BDC) positions SAP Datasphere as the semantic hub connecting SAP applications (S/4HANA, BW/4HANA) with cloud lakehouses (such as Databricks).

## 2. BW Data Product Generator
- **Capability**: Allows SAP BW/4HANA to publish existing InfoProviders (ADSOs, CompositeProviders) directly as curated Data Products in SAP Datasphere.
- **Data Subscriptions**: Manages automated delta synchronization into Datasphere Inbound Buffers.
- **Reference**: SAP Note 3590400 defines prerequisites for BW Data Product Generator integration.
