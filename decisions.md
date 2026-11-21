# HanaMorph Architectural Decision Records (ADRs)

## ADR-001: Strict Read-Only Policy on SAP System S21 (`int_samarth`)
- **Status**: Accepted / Active
- **Context**: The `int_samarth` credentials carry `SAP_ALL` administrative privileges on SAP System S21 (Client 200 and all clients).
- **Decision**: All automated agents, scripts, and connectors must strictly treat SAP S21 as read-only. No `POST`, `PUT`, `PATCH`, `DELETE` HTTP requests, no CTS transports (`TRKORR`), and no DDIC/ABAP/BW mutations are permitted.
- **Consequences**: Zero risk of inadvertent production/development system corruption. Artifacts are generated offline for manual developer deployment.

## ADR-002: Modular AI Agent Skills with Progressive Disclosure
- **Status**: Accepted / Active
- **Context**: Monolithic system prompts and large context dumps rapidly deplete model context budgets and induce cognitive degradation.
- **Decision**: Deploy lightweight, specialized `SKILL.md` units in `.agents/skills/`. Agents load domain instructions only on-demand when executing specific tasks.
- **Consequences**: Drastic reduction in token consumption, focused instruction adherence, and predictable quality gates.

## ADR-003: Deterministic Similarity & Risk Scoring Precedence
- **Status**: Accepted / Active
- **Context**: Generative models alone can hallucinate similarity or produce non-reproducible clustering of database objects.
- **Decision**: Multi-factor candidate scoring uses deterministic mathematics (Jaccard similarity, Levenshtein distance, graph intersection) combined with local embeddings. The LLM is restricted to explanation synthesis and human-review summaries.
- **Consequences**: Auditable, mathematically reproducible duplicate detection.

## ADR-004: External MCP Server Sandboxing (`sap-datasphere-mcp`)
- **Status**: Accepted / Active
- **Context**: `MarioDeFelipe/sap-datasphere-mcp` provides 41+ tools, including write-capable tools (`create_database_user`, `delete_database_user`, `reset_database_user_password`, `execute_query`).
- **Decision**: Keep `sap-datasphere-mcp` disconnected and strictly unconfigured during foundational setup. Any future integration must enforce read-only tool filtering and require explicit user consent.
- **Consequences**: Strict defense-in-depth preventing accidental state changes in Datasphere.

## ADR-005: Compact Persistent Memory Files for Token Optimization
- **Status**: Accepted / Active
- **Context**: Multi-session development frequently loses context or wastes thousands of tokens re-scanning file trees.
- **Decision**: Maintain compact memory files (`architecture.md`, `decisions.md`, `environment.md`, `current-state.md`, `next-steps.md`) updated incrementally only upon meaningful architectural state changes.
- **Consequences**: Fast session bootstrapping, minimal context overhead, and consistent execution.
