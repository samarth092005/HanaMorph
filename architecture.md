# HanaMorph System Architecture

## 1. System Mission & Scope
HanaMorph is an enterprise-grade intelligent decision-support and modernization engine designed to rationalize, detect duplicates, uncover semantic reuse opportunities, and orchestrate migration paths from legacy SAP BW / BW/4HANA / HANA DB assets into modern SAP Datasphere analytical models.

## 2. Core Architecture Pipeline

```
+-----------------------------------------------------------------------------------+
|                            SAP Landscape & Metadata Sources                       |
|   - SAP BW / BW/4HANA (ADSOs, Transformations, DTPs, DataSources, ODP)            |
|   - SAP HANA DB (Calculation Views, CDS Entities, SQLScript)                      |
|   - SAP Datasphere (Spaces, Tables, Graphical/SQL Views, Analytic Models, Catalog)|
+-----------------------------------------------------------------------------------+
                                          |  (Read-Only Metadata Ingestion)
                                          v
+-----------------------------------------------------------------------------------+
|                               Ingestion & Normalization Layer                     |
|   Extracts normalized schemas, field catalogs, lineage graphs, and usage metrics. |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Candidate Generation & Blocking Engine                     |
|   Domain-based blocking keys, measure clustering, and structural partitioning.    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Multi-Factor Scoring & Semantic Engine                     |
|   - Jaccard Structural Column Overlap                                             |
|   - Normalized Levenshtein / Token Ratio Name Match                               |
|   - Upstream Lineage & Dependency Graph Intersection                              |
|   - Local Vector Semantic Embeddings                                              |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     Blast Radius & Operational Risk Assessment                    |
|   Downstream consumption tracking, SAC story dependencies, and query volume.      |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                          Rationalization Decision Matrix                          |
|   CONSOLIDATE | POTENTIAL_DUPLICATE_REVIEW | REUSE_EXISTING | REBUILD | KEEP_BOTH |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       Governed Action Plan & Audit Trail                          |
|   Human-in-the-loop review, dual control separation, immutable SHA-256 logs.      |
+-----------------------------------------------------------------------------------+
```

## 3. Strict Safety Invariants
1. **SAP S21 Zero-Modification Invariant**: S21 inspection is 100% read-only. No DDIC, CDS, BW, or ABAP modifications, activations, or transports.
2. **Local Artifact Generation**: All generated migration scripts, CDS view entities, SQL, and documentation reside strictly in local workspace files.
3. **Deterministic Precedence**: Statistical algorithms and deterministic checks govern candidate generation; LLMs assist explanation and synthesis within strict bounds.
