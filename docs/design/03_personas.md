# Target personas and workflows

## Network Engineer (Day-2 operations) — Low-code user

Uses the **Portal** to request work. Doesn't need to understand Tasks or Workflows.

- "Change this interface to VLAN 123" → Submit form → Done
- "Add VLAN 123 to these trunk ports" → Submit form → Done
- "Upgrade this switch to IOS-XE 17.9" → Submit form → Approve → Done

Key needs:

- Simple, guided forms
- Preview before submit
- Status tracking
- No coding required

## Network Automation Engineer (Platform builder) — Pro-code user

Builds the automation that Network Engineers consume.

- Creates **Tasks** in the catalog
- Builds **Task Implementations** per vendor/platform
- Composes **Workflows**
- Designs **Request Forms**
- Integrates with Git, Secrets, ITSM, controller APIs

Key needs:

- Template editor + syntax highlighting
- Test mode for Tasks/Workflows
- Version control via Git
- Python hooks for advanced logic

## Security/Compliance Engineer

Uses the platform to ensure network security and compliance.

- Run compliance audits
- View vulnerability data
- Execute remediation workflows
- Review risk scores and prioritize patching

Key needs:

- Compliance dashboards
- CVE/risk integration
- Audit trail for all changes

## Auditor / Change Manager

Reviews and approves changes, generates compliance reports.

- Approve/reject pending Executions
- Review execution history (who/what/when/result)
- Export audit logs
- Generate change management reports

Key needs:

- Full audit trail
- Rendered artifacts + diffs
- Approval workflow integration
- Reporting
