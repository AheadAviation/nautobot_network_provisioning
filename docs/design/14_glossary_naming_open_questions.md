# Terminology glossary, naming, and open questions

## Terminology glossary

| Term | Definition |
|------|------------|
| **Task** | An abstract operation (e.g., "Change VLAN"). Vendor-agnostic definition of what to do. |
| **Task Implementation** | A platform-specific way to execute a Task (e.g., "Change VLAN on Cisco IOS-XE"). Contains templates or code. |
| **Workflow** | An orchestrated sequence of Tasks that accomplishes a business objective (e.g., "Change VLAN with validation and approval"). |
| **Request Form** | A user-facing form that exposes a Workflow via the self-service portal. |
| **Execution** | A record of a Workflow run—the full audit trail of what happened. |
| **Provider** | A driver that handles communication with devices or external systems (e.g., Netmiko, DNAC API, ServiceNow). |
| **Portal** | The self-service UI where operators submit Request Forms. |

### Key workflows enabled

**Configuration change** (e.g., Change VLAN):
```
User submits form → Workflow executes:
  1. Get current config (Task)
  2. Validate state matches Nautobot (Task)
  3. Apply change (Task - platform-specific)
  4. Save config (Task)
  5. Validate change applied (Task)
→ Execution record with full audit trail
```

**OS/firmware upgrade**:
```
User submits form → Workflow executes:
  1. Check Device Lifecycle Management for EoL/CVE data (Task)
  2. Pre-upgrade checks (Task)
  3. Backup config (Task)
  4. Upload image (Task)
  5. Execute upgrade (Task)
  6. Wait for reboot (Wait step)
  7. Post-upgrade validation (Task)
  8. Update Nautobot with new version (Task)
→ Execution record with backup reference
```

**Compliance audit**:
```
Scheduled or on-demand → Workflow executes:
  1. Get current config (Task)
  2. Run compliance checks (multiple Tasks)
  3. Record results (Task)
  4. If failures: trigger remediation Workflow or notify
→ Compliance report
```

## Naming and branding considerations

### Product naming

When choosing a name for this platform:

- **Avoid**: Names that are confusingly similar to "BackBox" (e.g., "BackBoxx", "Back*Box", "*Box")
- **Consider**: Names that reflect the platform's purpose:
  - Network automation / lifecycle management focus
  - Nautobot-native positioning
  - Open-source or extensible nature
- **Examples** (for inspiration only, verify trademark availability):
  - "Network Lifecycle Manager"
  - "Provisioning Automation Platform"
  - "Network Operations Hub"
  - "Nautobot Automation Suite"

### Terminology

Use generic, industry-standard terms rather than proprietary terminology:

- **"Policy Checks"** instead of "IntelliChecks" (BackBox trademark)
- **"Workflows"** instead of proprietary workflow names
- **"Tasks"** and **"Workflows"** (established in this design)
- **"Compliance Checks"** (standard term)
- **"Risk Scoring"** (standard term)
- **"Session Recording"** (standard term)

### Legal compliance

- **Clean-room development**: All code and design should be original, not copied from BackBox
- **Public information only**: Base design on publicly available information (marketing materials, public docs)
- **Trademark research**: Conduct thorough trademark search before finalizing product name
- **IP review**: Consider patent landscape review if planning commercial distribution
- **Documentation**: Maintain clear documentation of design decisions and sources

## Open questions

- How much expression language do we allow in Workflow step conditions (simple tags vs. Jinja vs. CEL vs. Python)?
- Do we model "intent updates" as a first-class object (ChangeSet) separate from Executions?
- How do we want to handle drift: periodic checks, on-demand checks, or "before apply" only?
- Should we build our own backup storage or always integrate with Golden Config?
- How granular should session recording be (all commands, only privileged commands, opt-in per user)?
- Should compliance checks be versioned like Tasks/Workflows?
- How do we handle multi-vendor upgrade workflows (Task Implementation selection handles this)?
- What's the right balance between UI simplicity and power user features?
- Should we support multi-tenancy (separate automation libraries per tenant/organization)?
