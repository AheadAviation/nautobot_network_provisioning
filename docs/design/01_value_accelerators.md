# 2025 value accelerators (high ROI)

These are “trend-aligned” capabilities that materially increase value for network teams and leadership.

## Drift detection (Current State vs Nautobot)

**Do not duplicate Golden Config.**

Problem: many teams struggle with **data integrity** (Nautobot intent vs what’s on the box).

Golden Config already covers configuration backup/compliance workflows and is the right place for “golden vs actual” configuration workflows (see [nautobot/nautobot-app-golden-config](https://github.com/nautobot/nautobot-app-golden-config)).

Proposal for this app:

- Provide a **first-class integration** with Golden Config where present (optional dependency), rather than re-implementing drift/compliance.
- Keep a lightweight **pre-flight sanity check** only for provisioning-critical attributes (e.g., interface VLAN/description/admin-state) where it directly prevents bad changes.

Integration approach:

- **Pre-flight check** step can call Golden Config’s APIs/jobs (when installed) for “actual vs intended” comparison or backup retrieval.
- **UI linking**: show “View Golden Config compliance/drift” links from Executions and Request Forms.
- **Gating**: optionally block a run if Golden Config reports non-compliance for a targeted feature set.

Key product advantage: we keep this app focused on **provisioning workflows**, while leveraging Golden Config for deeper configuration compliance.

## Vulnerability mapping (firmware/software vs CVEs)

Problem: firmware automation is increasingly coupled to security posture; teams want to know “is this device vulnerable?” at the moment they touch it.

Proposal:

- Add a **Vulnerability Check** step that can run during render/run.
- Input: device platform + software/firmware version (from Nautobot CFs and/or live facts).
- Output:
  - list of known CVEs / advisories affecting the current version
  - severity summary (CVSS, exploitability when known)
  - recommended “target versions” (if policy exists)

Implementation options (phased):

- Phase A: simple mapping from a curated JSON/YAML data set stored in Git (customer can manage it)
- Phase B: integrate optional external feeds (NVD, vendor advisories) with caching

This pairs naturally with Workflows: a Workflow can include a **security gate** step (block execution if high severity CVE found).

## Automated lifecycle management

Problem: network teams need to manage device onboarding, configuration backups, OS/firmware upgrades, and inventory synchronization as part of day-to-day operations.

Proposal:

- **Device onboarding automation**:
  - Discover devices via IP range, CIDR block, or CSV import
  - Automatically create/update Nautobot Device records with discovered facts
  - Apply initial configuration policies during onboarding
  - Support bulk onboarding workflows

- **Configuration backup and restore**:
  - Automated backup collection (scheduled or on-demand)
  - Store backups in Nautobot (or integrate with Golden Config)
  - One-click restore capability (restore config or OS to device, including bare metal replacements)
  - Backup validation and integrity checks
  - Version history and rollback support

- **OS and firmware upgrade automation**:
  - Multi-step upgrade workflows with pre/post checks
  - High-availability aware upgrades (upgrade standby first, etc.)
  - Automated testing after upgrades (connectivity, feature verification)
  - Rollback automation on failure
  - Upgrade scheduling and maintenance windows

- **Inventory synchronization**:
  - Periodic fact collection from devices
  - Update Nautobot Device records with current hardware/software info
  - Track end-of-life status and lifecycle planning
  - Alert on inventory discrepancies

Implementation approach:

- Use existing Tasks/Workflows framework for upgrade workflows
- Integrate with Golden Config for backup storage (optional)
- Create specialized Workflows (built from reusable Tasks) for onboarding, backup, and upgrade
- Use Nautobot Jobs for scheduled inventory sync
- Store backup artifacts in Nautobot or external storage (S3, Git)

## Compliance and policy automation

Problem: teams need to ensure devices comply with organizational policies, industry standards (DISA STIGs, CIS Benchmarks), and regulatory requirements.

Proposal:

- **Policy check library** (similar to BackBox's automation library):
  - Build a library of reusable policy checks (as Tasks)
  - Checks can validate configuration, Nautobot data, or live device state
  - Support for common standards (DISA STIGs, CIS Benchmarks, DORA, etc.)
  - Custom policy checks defined in UI or Git

- **Automated compliance auditing**:
  - Run policy checks on-demand or scheduled
  - Generate compliance reports per device, site, or organization
  - Track compliance status over time
  - Identify non-compliant devices and required remediations

- **Automated remediation**:
  - Link policy violations to remediation Workflows
  - One-click or scheduled remediation execution
  - Remediation approval workflows (optional)
  - Track remediation history and success rates

- **Change auditing and reporting**:
  - Track all configuration changes (who, what, when, why)
  - Compare configuration baselines
  - Generate audit reports for compliance teams
  - Integration with change management systems (ServiceNow, etc.)

Implementation approach:

- Policy checks implemented as Tasks (can be Jinja2 templates, API calls, or Python hooks)
- Compliance executions stored as Execution records (with per-step ExecutionStep results)
- Remediation uses existing Workflow framework
- Change audit trail stored in Nautobot (ObjectChange, custom audit models)
- Reports generated via Nautobot Jobs or external integrations

## Network discovery and mapping

Problem: teams need to discover network devices, map topology, and keep inventory accurate.

Proposal:

- **Device discovery**:
  - IP range scanning (ICMP, SNMP, SSH)
  - Credential-based discovery (try common credentials, use Secrets)
  - Controller-based discovery (DNAC, Meraki, Mist APIs)
  - Import from CSV/Excel

- **Topology mapping**:
  - Discover device relationships (LLDP, CDP, ARP tables)
  - Map interface connections
  - Update Nautobot Cable records automatically
  - Visualize network topology in Nautobot UI

- **Inventory enrichment**:
  - Collect device facts (model, serial, OS version, hardware specs)
  - Update Nautobot Device records with discovered data
  - Track software/firmware versions for vulnerability management
  - Identify end-of-life devices

Implementation approach:

- Discovery jobs run as Nautobot Jobs
- Use Netmiko/NAPALM for device access
- Store discovery results in Nautobot models
- Create/update Device, Interface, Cable records
- Optional: integrate with Nautobot's existing discovery capabilities

## Risk scoring and prioritization

Problem: teams need to prioritize which devices to patch/upgrade based on actual network risk, not just CVE severity.

Proposal:

- **Context-aware risk scoring**:
  - Consider device role (core vs. edge)
  - Consider network exposure (internet-facing, DMZ, internal)
  - Consider business criticality (from Nautobot custom fields/tags)
  - Combine CVE severity with network context

- **Risk-based prioritization**:
  - Rank devices by risk score
  - Recommend patching order
  - Identify high-risk devices requiring immediate attention
  - Generate risk reports for leadership

- **Automated risk remediation**:
  - Link high-risk findings to upgrade/remediation Workflows
  - Schedule automated remediation for low-risk items
  - Require approval for high-risk changes

Implementation approach:

- Risk scoring algorithm configurable per organization
- Store risk scores in Nautobot Custom Fields or dedicated model
- Risk calculation runs as part of vulnerability checks
- UI displays risk scores alongside vulnerability data

## Low-skill empowerment (UI-first “intent wizard”)

Problem: automation talent gap is real; value increases when the app works for non-experts.

Proposal:

- Provide **guided intents** (wizards) that produce:
  - a validated `intended` payload (JSON)
  - optionally Nautobot data updates (VLAN/VRF/IP assignment)
  - and a selected Workflow to render/apply

Design patterns:

- Safe defaults + “expert mode” escape hatch
- Preview-first workflow (show diff + explain)
- Guardrails:
  - policy checks (allowed VLAN ranges, naming conventions, VRF rules)
  - required approvals for certain operations
- Education embedded:
  - “why this change” explanations
  - highlight what data in Nautobot is missing / needs correction
