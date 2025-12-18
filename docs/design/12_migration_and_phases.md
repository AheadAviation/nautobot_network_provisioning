# Migration strategy and phased delivery plan

## Migration strategy (from current app)

This repository is treated as **net-new**; migration concerns and legacy models are intentionally out of scope.

---

## Phased delivery plan

### Phase 0 (current): Foundation

- Template rendering with structured context
- Basic template editor in UI
- Sample context with `device.interfaces`

### Phase 1: Task Catalog + Implementations

- Create `TaskDefinition` and `TaskImplementation` models
- UI for browsing Task Catalog
- UI for creating Task Implementations (template editor)
- Test Task against selected device
- Platform matching logic (Manufacturer → Platform → Software)

### Phase 2: Workflows

- Create `Workflow` and `WorkflowStep` models
- Visual workflow builder UI
- Step types: Task, Validation, Notification
- Test workflow in dry-run mode
- `Execution` model for audit trail

### Phase 3: Request Forms + Portal

- Create `RequestForm` and `RequestFormField` models
- Form builder UI (drag-and-drop fields)
- Self-service Portal UI
- Form → Workflow mapping
- Execution tracking UI

### Phase 4: Providers v1 (CLI)

- Netmiko/NAPALM/Scrapli providers
- Provider configuration UI
- Diff/preview support
- Safe apply with dry-run option

### Phase 5: Approval Workflows

- Approval step type in Workflows
- In-app approval UI
- Webhook callback support (for ITSM integration)
- Scheduled execution

### Phase 6: Providers v2 (Controllers + ITSM)

- DNAC provider
- Meraki provider
- ServiceNow integration provider
- Site/tenant → controller mapping

### Phase 7: Git Integration

- Import Tasks/Workflows from Git
- Export to Git
- Version tracking
- Sync status UI

### Phase 8: Lifecycle Workflows

- Pre-built Tasks: Get Config, Save Config, Backup, Restore
- Pre-built Workflows: Device Onboarding, OS Upgrade
- Integration with Device Lifecycle Management for EoL/CVE data
- Inventory sync jobs

### Phase 9: Compliance + Security

- Compliance check Tasks
- Compliance audit Workflows
- Risk scoring (integrate Device Lifecycle Management CVE data + network context)
- Session recording
