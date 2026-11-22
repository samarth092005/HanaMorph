# HANAMORPH Four-Studio Architecture Audit
**Scope:** Uploaded `HANAMORPH (2).zip` source snapshot  
**Mode:** Static, read-only source inspection  
**Date:** 2026-11-21

## Executive summary

The existing HANAMORPH application is a SAP CAP / Node.js backend with a SAPUI5 frontend. CDS View and Calculation View migration share a common UI pipeline controller and CAP service layer. Bulk Migration and Replication Flow Studio have dedicated controllers and call additional CAP actions.

The BW Migration Studio should reuse the platform's proven UI5 navigation conventions, CAP service patterns, job/log concepts, and artifact-generation conventions where suitable. It should not reuse the HANA-specific extraction logic as if it were a BW metadata connector, and it should not inherit deployment or authentication assumptions without remediation.

This is a static source audit. It does not establish that all flows run successfully in a live SAP environment.

## 1. Source inventory and architecture

### Runtime and dependencies
- CAP: `@sap/cds` `^9.9.4`
- CAP SQLite adapter: `@cap-js/sqlite` `^2.4.3`
- Datasphere CLI: `@sap/datasphere-cli` `^2026.22.0`
- HANA client: `@sap/hana-client` `^2.30.27`
- Express: `^4.21.0`
- XML parser: `fast-xml-parser` `^4.5.0`
- Authentication-related packages declared: `@sap/xssec`, `passport`
- Runtime configuration defaults to SQLite and dummy authentication in the inspected package manifest.

### Main structure
- UI: `app/controller`, `app/view`, `app/manifest.json`
- CAP model: `db/schema.cds`
- CAP service contract: `srv/migration-service.cds`
- CAP service handlers: `srv/migration-service.js`
- HANA extraction: `srv/lib/hana-connector.js`
- Source parsing: `srv/lib/extract-service.js`
- Datasphere generation: `srv/lib/transform-service.js`
- Datasphere deployment: `srv/lib/deploy-service.js`
- Runtime bootstrap: `srv/server.js`
- MTA deployment descriptor: `mta.yaml`

## 2. Four-studio audit

| Studio | UI controller | Main implementation pattern | Finding |
|---|---|---|---|
| CDS View Migration | `CdsPipeline.controller.js` | Extends `BasePipelineController` | Shared pipeline workflow |
| Calculation View Migration | `CalcViewPipeline.controller.js` | Extends `BasePipelineController` | Shared workflow with pipeline type specialization |
| Bulk Multi-View Migration | `BulkStudio.controller.js` | Dedicated JSONModel and CAP calls | Separate bulk selection, rationalization and generation workflow |
| Replication Flow Studio | `ReplicationStudio.controller.js` | Dedicated JSONModel and CAP calls | Separate orchestration and Datasphere replication workflow |

### CDS and Calculation View Studio
Both controllers are thin specializations of `BasePipelineController`. The base controller is large (1,195 lines) and manages search, view selection, artifact retrieval, column configuration, naming, generation and job handling.

The shared CAP service exposes:
- `searchViews`
- `listCDSViews`
- `listCalcViews`
- `getArtifacts`
- `getColumns`
- `startJob`
- `getJobStatus`
- `generateModularArtifacts`

The shared-controller pattern is useful, but the base controller is already large. The BW Studio should use focused components and domain-specific controllers rather than adding BW-specific branches to this controller.

### Bulk Multi-View Migration
`BulkStudio.controller.js` manages a separate multi-view selection state and calls:
- `listCDSViews`
- `listCalcViews`
- `rationalizeSources`
- `generateBulkArtifacts`

The backend exposes additional actions for source overlap and deduplication, including `extractAndDeduplicateTables`, `generateDeduplicatedReplicationPackage`, and `generateStarSchemaPackage`.

Reusable concept: selection cart, shared-source analysis, deduplication report, and package-level generation. These concepts need BW-specific dependency and semantic rules.

### Replication Flow Studio
`ReplicationStudio.controller.js` maintains its own target-space, source-connection, load-mode and flow-name state. It calls:
- `extractAndDeduplicateTables`
- `generateDeduplicatedReplicationPackage`
- `generateModularArtifacts`
- `deployTableAndReplicationFlow`
- `runReplicationFlow`
- `getReplicationFlowStatus`

This provides an existing example of separating preparation from deployment orchestration. However, deployment and run actions are write-capable and must not be reused in the BW discovery path.

## 3. Shared CAP model and service

### Existing CDS entities
- `SourceCatalog`
- `ViewArtifacts`
- `MigrationJobs`
- `JobLogs`

`MigrationJobs` contains source and target identifiers, status, progress, generated CSN/SQL, error message, row counts and composed logs.

This is a useful starting point for a BW-specific job model, but the existing model is tailored to views and should not be overloaded with BW object-specific fields.

### Existing CAP operations
The service defines query functions for catalog, columns and artifacts; actions for rationalization and artifact generation; and write-capable Datasphere deployment/run operations.

The BW Studio should have its own service boundary and entities for BW systems, discovery runs, BW objects, dependencies, assessment results, migration plans, generated artifacts, validation results and audit events.

## 4. Reuse recommendations

### Reuse after review
1. UI5 application shell, routing and navigation conventions.
2. CAP service organization and error-handling conventions.
3. Job lifecycle and log concepts.
4. CSN/JSON artifact handling patterns.
5. Existing UI design language and busy/error-state patterns.
6. Test organization and local configuration conventions.

### Do not directly reuse
1. HANA catalog extraction as a BW metadata source.
2. HANA-specific SQL parsing as a BW transformation parser.
3. Existing fixture catalogs as evidence of live BW inventory.
4. Existing replication deployment operations in read-only discovery.
5. Existing default authentication configuration for production.
6. Existing shell command construction without replacing it with safe argument-based process execution and strict input validation.

## 5. Security and operational findings

### High priority
- The inspected CAP service model contains no `@requires` or `@restrict` declarations. Authentication packages in `package.json` do not by themselves prove that service authorization is enforced.
- `deploy-service.js` uses `child_process.exec` with command strings containing interpolated values. This creates command-injection risk if any interpolated value is not strictly validated. Prefer argument-array process execution, allowlists and a narrowly scoped deployment adapter.
- HANA TLS certificate validation is configured through `sslValidateCertificate` and the inspected configuration code defaults this setting to `false`. Production connections should validate certificates.
- The inspected package manifest configures dummy authentication. This is acceptable only for isolated local development, not a client-facing production deployment.

### Additional review required
- `config.json` contains credential-shaped configuration keys. Inspect values only in a secure local process; never print them in audit output. Verify whether the file is tracked and rotate any credentials that were exposed.
- The uploaded archive contains a path named `datasphere-secrets.json`. Its contents were not reproduced in this report. Confirm whether it contains real credentials and whether it is tracked in Git history.
- Review all shell-command construction sites, logs, CORS policy, CSRF protections, secrets handling and dependency advisories before production.
- `.gitignore` excludes `*.sqlite`, but it does not visibly exclude `datasphere-secrets.json` by name.

## 6. BW Studio architecture recommendation

Build BW Migration Studio as a separate domain module within the HANAMORPH platform:

- UI5: dedicated BW Studio routes, views, controllers and reusable BW components.
- CAP: dedicated BW service and domain handlers.
- Metadata domain: BW system, source release, InfoArea, DataSource, InfoObject, InfoProvider, ADSO, Transformation, DTP, CompositeProvider, Query, Process Chain and dependency records.
- Discovery: read-only adapters with explicit capability checks.
- Assessment: transparent rules with evidence and confidence, not opaque hardcoded recommendations.
- Generation: local artifact generation only until separately approved deployment.
- Validation: structural checks, semantic checks and data reconciliation.
- Governance: immutable discovery and action audit events, explicit approvals and a default-deny policy for remote mutations.

Keep the four migration routes distinct in assessment:
1. Native Datasphere modernization.
2. SAP BW Bridge.
3. BDC Data Product Generator.
4. Hybrid coexistence.

Do not hard-code one-to-one mappings or a route before source release, object semantics, custom logic, dependencies, delta behavior and business requirements are assessed.

## 7. Priority remediation backlog

| Priority | Item | Reason |
|---|---|---|
| P0 | Verify and remediate tracked secrets | Prevent credential exposure |
| P0 | Replace dummy auth with real authentication and authorization for deployed environments | Protect client data and operations |
| P0 | Secure deployment process execution | Prevent command injection |
| P0 | Enforce TLS certificate validation | Protect system connections |
| P1 | Separate BW CAP service and domain model | Avoid coupling BW to HANA view migration |
| P1 | Define canonical BW metadata schema and lineage model | Foundation for reliable discovery |
| P1 | Add read-only adapter contract and deny-by-default policy | Preserve source-system safety |
| P1 | Add evidence-backed route assessment | Avoid unsupported migration recommendations |
| P2 | Decompose oversized shared UI controller | Reduce coupling and regression risk |
| P2 | Add contract, integration and end-to-end tests | Verify real user-visible behavior |

## 8. Verification limitations

This audit inspected source files from the uploaded ZIP. It did not:
- execute the application or its test suite;
- validate a live HANA connection;
- authenticate to S21;
- inspect a live Datasphere tenant;
- deploy or run a Datasphere replication flow;
- verify the current Windows working-tree state;
- prove that the ZIP's Git metadata exactly matches the current remote branch.

The new BW Studio scaffold branch is a separate source snapshot and must be reviewed independently before integration.
