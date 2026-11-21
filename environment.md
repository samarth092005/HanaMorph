# HanaMorph Environment Configuration

## 1. Host Infrastructure
- **Operating System**: Windows (x64)
- **Primary Shell**: PowerShell 7 / Windows PowerShell
- **Python Runtime**: Python 3.10+ / 3.14 (Virtual Environment configured in related paths)
- **Node.js**: Node v20 LTS
- **Package Managers**: `pip`, `npm`, `uv`

## 2. Workspace Layout
- **Workspace Path**: `C:\Users\samarth\BW-hanamorph`
- **Agent Skills Directory**: `C:\Users\samarth\BW-hanamorph\.agents\skills`
- **Related References**: `C:\Users\samarth\sap-bw-datasphere-rationalization-engine` (prior benchmark/reference implementation)

## 3. SAP Landscape Boundaries
- **System S21**:
  - User: `int_samarth`
  - Authorization Profile: `SAP_ALL`
  - Access Level: **STRICT READ-ONLY** (No DDIC, BDEF, CDS, or BW writes)
- **SAP Datasphere**:
  - Access Protocol: OAuth 2.0 Client Credentials (evaluated; inactive)
  - Tooling: `@sap/datasphere-cli` (datasphere CLI)
  - Write Access: **DISABLED / REQUIRES EXPLICIT APPROVAL**

## 4. Installed Agent Skills
| Skill Name | Upstream Source | License | Functional Domain |
|---|---|---|---|
| `spec-driven-development` | `addyosmani/agent-skills` | MIT | Requirements specification & PRD drafting |
| `context-engineering` | `addyosmani/agent-skills` | MIT | Context curation & token budget optimization |
| `code-review-and-quality` | `addyosmani/agent-skills` | MIT | Multi-axis code reviews & quality gates |
| `test-driven-development` | `addyosmani/agent-skills` | MIT | Red-green-refactor testing methodology |
| `agentic-verification` | `timini/agentic-verification` | MIT | Fault injection & test gap verification |
| `what-could-break` | `stas4000/what-could-break` | MIT | Regression & impact blast-radius analysis |
| `session-handoff` | `sickn33/agentic-awesome-skills` | MIT | State continuity & session handoffs |
| `sap-datasphere-engineer` | HanaMorph Custom Skill | Custom / Internal | SAP BW, HANA, Datasphere & CLI architecture |

## 5. Security & Sensitive Data Policy
- No credentials, API tokens, passwords, or `.env` files are stored in Git or echoed in chat/artifacts.
- All connections to external systems require verified read-only authorization.
