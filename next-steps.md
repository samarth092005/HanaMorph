# HanaMorph Recommended Next Steps

## 1. Immediate Next Step (Phase 1 Inception)
Before writing application code, use the installed `spec-driven-development` skill to draft the formal HanaMorph Technical Specification & Capability Map:
- Define the metadata schema for SAP BW extractors (ADSOs, Transformations, CompositeProviders).
- Define the schema for target SAP Datasphere objects (Tables, SQL Views, Analytic Models).
- Specify the candidate generation blocking key algorithms.

## 2. Subsequent Milestones
1. **Milestone 1: Project Scaffolding & Virtual Environment Setup**:
   - Initialize Python virtual environment with dependency pinning (`requirements.txt` / `pyproject.toml`).
   - Configure pytest suite using `test-driven-development` skill.
2. **Milestone 2: Deterministic Metadata Ingestion Engine**:
   - Build read-only offline mock data fixtures representing S21 BW objects and Datasphere spaces.
   - Implement data ingestion parsers with strict type safety.
3. **Milestone 3: Multi-Factor Scoring & Lineage Graph**:
   - Implement Jaccard similarity, string distance, and graph dependency intersection algorithms.
   - Run `agentic-verification` to inject mutants and verify test suite fault detection.
4. **Milestone 4: Blast Radius & Impact Analysis**:
   - Integrate `what-could-break` patterns into operational risk scoring.
5. **Milestone 5: Controlled Action Planner & Tamper-Evident Audit Trail**:
   - Implement SHA-256 event log chain and human-in-the-loop review approvals.

## 3. Pre-Flight Checklist Before Resuming Work
- [ ] Review `current-state.md` and `decisions.md`.
- [ ] Invoke `context-engineering` if entering complex subtasks to maintain token budget.
- [ ] Ensure any future MCP integration with Datasphere strictly restricts write permissions.
