# HANAMORPH — Known Limitations & Technical Boundaries

## 1. PURPOSE
This document outlines the current technical boundaries, unsupported legacy constructs, and edge cases in HANAMORPH BW Migration Studio.

---

## 2. TECHNICAL LIMITATIONS MATRIX

### 2.1 ABAP & Custom Code Boundaries
- **Dynamic ABAP Code**: Start or end routines employing dynamic code execution (`GENERATE SUBROUTINE POOL`, `CALL 'SYSTEM'`, or dynamic internal table construction) cannot be automatically translated to ANSI/HANA SQL. These routines are flagged as `COMPLEX` or `HIGHLY COMPLEX` and routed to **SAP BW Bridge**.
- **External C / RFC Calls**: Transformations invoking remote RFC function modules (`CALL FUNCTION ... DESTINATION`) cannot execute within Datasphere native views. They must remain in BW Bridge or be redesigned using SAP BTP Integration Suite.
- **Obsolete BEx 3.x Queries**: Queries created prior to BW 7.0 that have not been converted to 7.x BEx Query Designer format (`ELEM`) must be converted in BW first or imported via canonical bundle.

### 2.2 Graph & Lineage Boundaries
- **Hard Cycles in Lineage**: Topological DAG sequencing detects circular data flows. While soft cycles (feedback loops between distinct phases) are decoupled into ordered waves, hard cyclic table dependencies trigger a redesign warning requiring user refactoring before plan approval.
- **Cross-System Lineage Gaps**: If upstream DataSources reside in legacy systems not cataloged in the discovery snapshot, lineage edges terminate with confidence rating < 1.0.

### 2.3 Concurrency & Scaling Boundaries
- **Single-Writer SQLite Queue**: Write operations are serialized through `SingleWriterQueue`. While reader concurrency is horizontally scalable via WAL mode, sustained write throughput is bounded by single-disk fsync speed (up to ~2,500 object writes per second).
- **In-Memory Queue Capacity**: The default write queue capacity is 1,000 items. Bursts exceeding this capacity invoke backpressure mechanisms (`QueueFull` exception) to protect process memory.

### 2.4 SAP Target Limitations
- **Datasphere Space Identifier Length**: Datasphere restricts space technical names to 30 characters.
- **CSN View Join Depth**: Complex CompositeProviders with deep nested joins (> 15 joins) are flagged by Level 7 deployment validation for performance review in SAP Datasphere.
