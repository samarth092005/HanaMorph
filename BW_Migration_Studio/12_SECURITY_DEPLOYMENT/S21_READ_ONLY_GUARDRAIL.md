# S21 Read-Only Security Guardrail & Enforcement

## 1. Threat Model & Invariant
- **Administrative Account**: User `int_samarth` possesses `SAP_ALL` administrative privileges on SAP System S21 (Client 200).
- **Invariant**: Under NO circumstances shall any HanaMorph module, script, or agent issue mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) to S21.
- **Enforcement**:
  1. The connector layer implements a strict HTTP verb whitelist: only `GET` and `HEAD` requests are dispatched.
  2. Any call attempting to create CTS Transports (`TRKORR`), modify DDIC structures, or trigger DTP loads throws an immediate `SecurityViolationError` and halts execution.
  3. No credentials or secret tokens are ever committed to Git or written to persistent logs.
