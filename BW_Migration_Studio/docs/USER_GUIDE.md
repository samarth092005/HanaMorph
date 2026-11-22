# HANAMORPH — End-to-End User Journey Guide

## 1. INTRODUCTION & WORKFLOW OVERVIEW
HANAMORPH BW Migration Studio provides a streamlined, step-by-step modernization workbench that guides architects, consultants, and developers from legacy SAP BW discovery to sealed, validated cloud delivery packages.

```
[1. Connect] ➔ [2. Discover] ➔ [3. Assess] ➔ [4. Plan & Approve]
       ➔ [5. Generate] ➔ [6. Validate] ➔ [7. Package & Deliver]
```

---

## 2. STEP-BY-STEP USER WALKTHROUGH

### Step 1: Connect & Verify
1. Access HANAMORPH in your web browser at `http://localhost:4004`.
2. Navigate to the **Connections** tab.
3. Review configured connection parameters for SAP BW (`S21`), SAP Datasphere, and SAP BTP.
4. Click **Test S21 Connection** to confirm read-only connectivity and latency.
5. All tests run non-mutating diagnostics (`GET` and `RFC_PING`); no changes are written to SAP.

### Step 2: Metadata Discovery
1. Click the **Discovery** tab.
2. Choose your discovery mode:
   - **Live Discovery**: Extracts active metadata from connected SAP systems.
   - **Import Bundle**: Ingests offline JSON/XML metadata bundles without network connectivity.
3. Click **Start Discovery**.
4. Monitor the live progress bar as DataSources, InfoObjects, ADSOs, Transformations, and Process Chains are ingested.
5. Inspect the object inventory table and filter by TLOGO type or provenance badge (`LIVE_VERIFIED`, `CACHED`, `IMPORTED`).

### Step 3: Migration Assessment
1. Click the **Assessment** tab.
2. Click **Run Assessment** to evaluate all discovered objects.
3. Review the multi-dimensional radar chart and overall scores:
   - **Functional Fit**: Alignment with modern analytical paradigms.
   - **Technical Complexity**: Impact of ABAP/AMDP routines and transformations.
   - **Process & Delta**: Lineage and scheduling feasibility.
4. Review the **4-Route Recommendations**:
   - `native_datasphere`: Cloud-native entities and views.
   - `bw_bridge`: ABAP-based extractor staging.
   - `bdc_data_product`: Enterprise data contracts.
   - `hybrid`: Two-tier staging and semantic modeling.

### Step 4: Architecture Planning & DAG Sequencing
1. Click the **Planning** tab.
2. Create a new migration project by specifying Project Name and Target Route.
3. Click **Generate Plan**. The engine executes topological DAG sequencing to determine optimal migration waves and identify any cyclic dependencies.
4. Review the migration waves.
5. Click **Approve Plan**. Approval is mandatory before artifact generation is unlocked.

### Step 5: Artifact Generation
1. Click the **Generation** tab.
2. Ensure the approved plan is selected.
3. Click **Generate Artifacts**.
4. Inspect the generated assets in the preview pane:
   - `.csn.json`: SAP Core Schema Notation entity definitions.
   - `.sql`: SAP HANA Cloud column table DDL statements.
   - `_mapping.md`: Source-to-target field mapping documentation.
5. Files are written locally to `output/<project_id>/<plan_id>/`.

### Step 6: 7-Level Validation
1. Click the **Validation** tab.
2. Click **Run Validation**.
3. The engine runs 119 automated checks across Syntax, Schema, Lineage, Delta, Business Rules, Security, and Deployment.
4. Verify that `failed_checks == 0` and Quality Score >= 80%.

### Step 7: Sealed Delivery Packaging
1. Click the **Delivery** tab.
2. Click **Package for Delivery**.
3. The packager bundles all validated assets, generates `manifest.json`, seals the archive with a SHA-256 checksum, and creates `package.zip`.
4. Click **Download Sealed Package** to save the deployment bundle locally for import into SAP Datasphere.
