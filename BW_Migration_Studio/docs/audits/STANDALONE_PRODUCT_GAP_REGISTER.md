# BW MIGRATION STUDIO — STANDALONE PRODUCT GAP REGISTER
**Document:** Technical Debt, Architecture Gaps & Limitations Register  
**Auditor:** Principal Enterprise Architect  
**Status:** **AUTHORITATIVE**  

---

## 1. Gap Classification Matrix

| Gap ID | Domain | Severity | Title & Technical Description | Impact | Recommended Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | Architecture | **MEDIUM** | Dual SQLite Database Location | `database/bw_studio.sqlite` holds canonical data, but `verify_synthetic_e2e.py` writes to `bw-studio/bw_studio.sqlite`. | Update `verify_synthetic_e2e.py` to target canonical database path and remove redundant root sqlite file. |
| **GAP-02** | Security | **MEDIUM** | Unauthenticated REST API Endpoints | Port 4004 serves all `/api/*` endpoints without authentication or API token validation. | Implement `Authorization: Bearer <token>` middleware in `server.py` validated against `.env`. |
| **GAP-03** | Runtime | **MEDIUM** | Synchronous Single-Threaded HTTP Server | `server.py` inherits from `http.server.BaseHTTPRequestHandler` without threading mixin. Long queries block other requests. | Inherit from `socketserver.ThreadingMixIn` or migrate to a lightweight ASGI runner (Uvicorn / FastAPI). |
| **GAP-04** | Packaging | **LOW** | Missing Python Dependency Declarations | No `requirements.txt` or `pyproject.toml` exists. New developers must guess required packages. | Add `requirements.txt` documenting Python 3.10+ standard library plus `cryptography` and optional `pyrfc`. |
| **GAP-05** | Packaging | **LOW** | Delivery Bundle Not Zipped Automatically | `DeliveryPackager` stages uncompressed directories with `manifest.json` but does not produce a final `.zip` archive. | Add `shutil.make_archive` call at the end of `create_package()` to generate `bundle.zip`. |
| **GAP-06** | UI / Frontend | **LOW** | Monolithic Frontend Architecture | `frontend/index.html` contains all 980 lines of HTML, CSS, and JS in a single file. | Separate into `css/studio.css`, `js/app.js`, and HTML view partials for maintainability. |
| **GAP-07** | UI / Lineage | **LOW** | Relational Table Lineage Display | Screen 5 displays upstream/downstream lineage as HTML tables instead of an interactive visual node-link graph. | Integrate a lightweight SVG / Canvas DAG renderer (e.g. D3.js or Cytoscape) for visual lineage exploration. |
| **GAP-08** | SAP BW | **INFO** | NetWeaver 7.53 BWMT REST Endpoints 404 | Source S21 system lacks BW Modeling Tools REST endpoints (`/sap/bc/adt/bw/*`). | Handled by design via Eclipse BWMT XML workspace cache ingestion (`.bw/`). Document as expected constraint. |
