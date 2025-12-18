# UI design (Automation tab)

The navigation is organized to support the workflow from building blocks → orchestration → self-service.

## Automation → Portal (self-service)

The "front door" for operators. Clean, simple, focused on getting work done.

- Grid/list of published Request Forms
- Filter by category, tags, recent
- Each card shows: name, description, "Start" button
- Recent executions for quick access
- No technical details visible—just user-friendly forms

## Automation → Executions

View all workflow executions (runs).

- List with filters: status, workflow, user, date range, device
- Status indicators: pending, running, awaiting approval, completed, failed
- Click to see execution details:
  - Step-by-step progress
  - Rendered configs/payloads
  - Logs and outputs
  - Diff views (before/after)
  - Approval history

## Automation → Request Forms

Build user-facing forms for the portal.

- CRUD Request Forms
- Form builder UI:
  - Drag-and-drop field ordering
  - Field types: object selector, text, number, choice, boolean
  - Conditional visibility (show field X if field Y = Z)
  - Validation rules
  - Help text and placeholders
- Link to Workflow
- Preview mode (test the form)
- Publish/unpublish toggle

## Automation → Workflows

Orchestrate Tasks into end-to-end processes.

- CRUD Workflows
- Visual step builder:
  - Add steps (Task, Validation, Approval, Notification, Condition, Wait)
  - Drag to reorder
  - Configure each step's inputs/outputs
  - Set conditions and failure behavior
- Test mode:
  - Select target device(s)
  - Provide sample inputs
  - Dry-run execution (render only, no push)
- Version history

## Automation → Task Catalog

Browse and manage the catalog of available operations.

- List of TaskDefinitions organized by category
- For each Task:
  - Description of what it does
  - Input/output schemas
  - List of implementations (by platform)
  - "Add Implementation" button
- Create new Tasks

## Automation → Task Implementations

Create platform-specific implementations.

- Guided creation flow:
  1. Select Task (e.g., "Change VLAN")
  2. Select Manufacturer (e.g., "Cisco")
  3. Select Platform (e.g., "IOS-XE") – filtered by manufacturer
  4. Optionally specify Software Version pattern
  5. Choose implementation type (Jinja2, API call, Python hook)
  6. Write/configure the implementation
  7. Test against sample device
- Template editor with:
  - Syntax highlighting
  - Variable autocomplete (from input schema)
  - Live preview with sample data
  - Validation/linting

## Automation → Providers

Configure connection drivers and external integrations.

- List of configured providers
- For each provider:
  - Connection settings (credentials via Secrets)
  - Scope (which sites/tenants use this provider)
  - Test connection button
- Add new provider configurations

## Automation → Git Sync

Manage Git integration for version control.

- Connect Git repositories
- Import: Pull Tasks, Implementations, Workflows from Git
- Export: Push UI-created content to Git
- Sync status and history
- Conflict resolution UI

## Automation → Lifecycle

Pre-built workflows for common lifecycle operations.

- **Device Onboarding**:
  - Discovery job creation and execution
  - Bulk import from CSV
  - Onboarding workflow configuration
  - View discovered devices and import status

- **Backups**:
  - View backup history per device
  - One-click restore interface
  - Backup scheduling and automation
  - Backup validation and integrity checks

- **Upgrades**:
  - Create upgrade plans (query Device Lifecycle Management for EoL/CVE data)
  - Schedule upgrades
  - Monitor upgrade progress
  - View upgrade history and rollback options

- **Inventory Sync**:
  - Configure sync schedules
  - View sync history
  - Compare Nautobot data vs. live device facts
  - Resolve inventory discrepancies

## Automation → Compliance

Policy checks and remediation workflows.

- **Policy Checks**:
  - CRUD policy check definitions (as Tasks)
  - Test checks against devices
  - View check library (filter by standard, severity, etc.)

- **Compliance Audits**:
  - Run compliance audits (on-demand or scheduled)
  - View compliance status dashboard
  - Filter by device, site, compliance standard
  - Generate compliance reports

- **Remediation**:
  - View failed compliance checks
  - One-click remediation (execute remediation Workflow)
  - Track remediation history
  - Approve/reject remediation actions

## Automation → Security

Integration with Device Lifecycle Management for vulnerability data.

- **Vulnerabilities** (data from Device Lifecycle Management):
  - View device vulnerability status
  - CVE details and risk scores
  - Prioritized remediation recommendations
  - Link to remediation Workflows

- **Risk Scoring**:
  - View device risk scores (CVE severity + network context)
  - Risk score calculation details
  - Risk-based prioritization dashboard
  - Risk trend analysis

- **Session Audit**:
  - View terminal session records
  - Search sessions by device, user, date
  - Review command history
  - Export session logs for compliance
