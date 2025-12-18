# Security, RBAC, and audit

- Use Nautobot object permissions for:
  - who can edit Tasks/Workflows
  - who can execute Executions
  - who can approve Executions
- Record:
  - requester, approver, timestamps
  - rendered artifacts and diffs
  - provider logs (redacted)
- Enforce secrets hygiene:
  - store tokens/passwords in Nautobot Secrets
  - redact secrets in logs/artifacts
