# Repository Comparison: HanaMorph Baselines

| Dimension | `Varad-6/HANAMORPH` | `aaratidhaigude/HANAMORPH` | `sap-bw-datasphere-rationalization-engine` |
|---|---|---|---|
| **Primary Focus** | CDS & Calculation Views to Datasphere | CDS & Calculation Views to Datasphere | Datasphere Object Rationalization & Duplicate Detection |
| **Active Branch** | `update-2` (pushed 2026-11-20) | `update-2` (pushed 2026-11-19) | `main` |
| **Backend Tech** | SAP CAP Node.js (`@sap/cds` 9.9.4) | SAP CAP Node.js (`@sap/cds` 9.9.4) | Python FastAPI + ChromaDB |
| **Frontend Tech** | SAPUI5 / Fiori XML Views | SAPUI5 / Fiori XML Views | React / Next.js Dashboard |
| **Persistence** | SQLite (`db.sqlite`) | SQLite (`db.sqlite`) | SQLite (`rationalization.db`) |
| **Replication Flows** | Yes (`ReplicationStudio`) | Yes (`ReplicationStudio`) | No (Metadata & Analysis only) |
| **Verdict** | **Authoritative HanaMorph Baseline** | Upstream Fork | Complementary Rationalization Reference |
