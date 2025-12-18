# Data model (proposed) and context schema

## Data model (proposed)

This data model uses clear, descriptive names and supports both low-code and pro-code usage patterns.

### `TaskDefinition` (the Task Catalog)

Represents an abstract operation (vendor-agnostic "what to do").

- **name** (unique): Human-readable name (e.g., "Change VLAN")
- **slug**: URL-safe identifier
- **description**: What this task does
- **category**: Grouping (Configuration, Validation, ITSM, Lifecycle, etc.)
- **input_schema**: JSON Schema defining required inputs
- **output_schema**: JSON Schema defining outputs
- **tags**: For filtering/organization
- **documentation**: Markdown help text

### `TaskImplementation` (platform-specific "how to do it")

A concrete implementation of a Task for a specific vendor/platform/software.

- **task** (FK to TaskDefinition)
- **name**: Descriptive name (e.g., "Change VLAN - Cisco IOS-XE")
- **manufacturer** (FK to Manufacturer): Required
- **platform** (FK to Platform): Optional, for more specific matching
- **software_version_pattern**: Regex or semver range (e.g., "17.*", ">=15.0,<16.0")
- **priority**: Integer for match precedence (higher wins)
- **implementation_type**:
  - `jinja2_config` (render CLI config text)
  - `jinja2_payload` (render structured payloads)
  - `api_call` (HTTP request)
  - `graphql_query` (query Nautobot)
  - `python_hook` (pro-code: custom Python function)
- **template_content**: Jinja2 template (for template types)
- **action_config**: JSON (for api_call, graphql_query, python_hook)
- **pre_checks**: List of validation steps before execution
- **post_checks**: List of validation steps after execution
- **provider** (FK to Provider, optional): Override default provider selection
- **enabled**: Boolean

### `Workflow` (orchestrated sequence of Tasks)

An end-to-end automation workflow composed of ordered steps.

- **name**
- **slug**
- **description**
- **category**
- **version**: Semantic version
- **enabled**
- **approval_required**: Boolean
- **schedule_allowed**: Boolean
- **input_schema**: JSON Schema for workflow inputs (combined from tasks)
- **default_inputs**: JSON default values

### `WorkflowStep` (individual step in a Workflow)

- **workflow** (FK to Workflow)
- **order**: Integer position in workflow
- **name**: Step display name
- **step_type**: `task` | `validation` | `approval` | `notification` | `condition` | `wait`
- **task** (FK to TaskDefinition, for task steps)
- **input_mapping**: JSON (how to map workflow context to step inputs)
- **output_mapping**: JSON (how to capture step outputs to context)
- **condition**: Jinja2 expression (when to execute this step)
- **on_failure**: `stop` | `continue` | `skip_remaining`
- **config**: JSON (step-type-specific configuration)

### `RequestForm` (user-facing portal form)

Exposes a Workflow to end users via self-service portal.

- **name**
- **slug**
- **description**: User-friendly explanation
- **workflow** (FK to Workflow)
- **published**: Boolean (visible in portal)
- **category**: For portal organization
- **icon**: Optional icon for portal display

### `RequestFormField` (individual form field)

- **form** (FK to RequestForm)
- **order**: Integer position
- **field_name**: Internal name (maps to workflow input)
- **field_type**: `object_selector` | `text` | `number` | `choice` | `multi_choice` | `boolean`
- **label**: Display label
- **help_text**: User guidance
- **required**: Boolean
- **default_value**: JSON
- **validation_rules**: JSON (regex, range, etc.)
- **choices**: JSON (for choice/multi_choice types)
- **object_type**: ContentType (for object_selector: Device, Interface, VLAN, etc.)
- **queryset_filter**: JSON (filter available objects)
- **depends_on**: FK to another field (for conditional visibility)
- **show_condition**: Jinja2 expression

### `Execution` (audit record of a workflow run)

- **workflow** (FK to Workflow)
- **request_form** (FK to RequestForm, optional)
- **requested_by** (FK to User)
- **approved_by** (FK to User, optional)
- **status**: `pending` | `running` | `awaiting_approval` | `scheduled` | `completed` | `failed` | `cancelled`
- **inputs**: JSON snapshot of all inputs
- **context**: JSON accumulated context during execution
- **scheduled_for**: DateTime (for scheduled execution)
- **started_at**, **completed_at**: DateTime
- **target_devices**: M2M to Device (for filtering/reporting)

### `ExecutionStep` (per-step execution details)

- **execution** (FK to Execution)
- **workflow_step** (FK to WorkflowStep)
- **order**: Integer
- **status**: `pending` | `running` | `completed` | `failed` | `skipped`
- **started_at**, **completed_at**: DateTime
- **task_implementation** (FK to TaskImplementation, if task step)
- **rendered_content**: Text (rendered template/payload)
- **inputs**: JSON (resolved inputs for this step)
- **outputs**: JSON (captured outputs)
- **logs**: Text
- **error_message**: Text (if failed)

### `Provider` (driver type)

Represents a driver for communicating with devices or external systems.

- **name**: Identifier (e.g., `netmiko`, `napalm`, `dnac`, `servicenow`)
- **driver_class**: Python path to driver class
- **description**
- **capabilities**: JSON list of what this provider can do
- **supported_platforms**: M2M to Platform (optional)

### `ProviderConfig` (instance configuration)

- **provider** (FK to Provider)
- **name**: Instance name (e.g., "Production DNAC", "Lab Meraki Org")
- **scope_sites**: M2M to Site (optional)
- **scope_tenants**: M2M to Tenant (optional)
- **scope_tags**: M2M to Tag (optional)
- **credentials** (FK to SecretsGroup)
- **settings**: JSON (base_url, timeout, retries, etc.)
- **enabled**: Boolean

### Legacy notes

This repository is treated as **net-new**; legacy models and migration notes are intentionally out of scope.

### `BackupRecord` (configuration backup)

Represents a device configuration or OS backup.

- **device** (FK to Device)
- **backup_type**: `config` | `os_image` | `full`
- **backup_data**: text blob (config) or file reference (OS image)
- **backup_method**: how backup was collected (CLI, API, Golden Config, etc.)
- **backup_timestamp**
- **validated**: boolean (backup integrity check passed)
- **restore_count**: number of times this backup has been restored
- **metadata**: JSON (device facts at time of backup, version info, etc.)

### `ComplianceCheck` (policy check definition)

Represents a reusable policy check.

- **name**, **description**
- **check_type**: `config_template` | `graphql_query` | `api_call` | `python_hook`
- **standard**: optional (DISA STIG, CIS Benchmark, DORA, custom)
- **severity**: `info` | `warning` | `error` | `critical`
- **check_logic**: template/query/code to execute
- **remediation_workflow** (FK, optional): Workflow to run if check fails
- **match_rules**: when to apply this check (platform, role, site, tags)

### `ComplianceRun` (compliance audit execution)

Represents a compliance check execution.

- **device** (FK, or scope query)
- **check** (FK to ComplianceCheck)
- **status**: `passed` | `failed` | `error` | `skipped`
- **result_data**: JSON (details of what was checked, what failed)
- **remediation_execution** (FK to Execution, if remediation was executed)
- **run_timestamp**, **requested_by**

### `UpgradePlan` (OS/firmware upgrade workflow)

Represents a planned or executed upgrade.

- **device** (FK, or scope query)
- **current_version**: software/firmware version before upgrade
- **target_version**: desired version
- **upgrade_workflow** (FK to Workflow)
- **status**: `planned` | `scheduled` | `in_progress` | `completed` | `failed` | `rolled_back`
- **pre_check_results**: JSON (connectivity, feature tests before upgrade)
- **post_check_results**: JSON (validation tests after upgrade)
- **backup_reference** (FK to BackupRecord)
- **scheduled_time** (optional)
- **execution** (FK to Execution)

### `DiscoveryJob` (network discovery execution)

Represents a device discovery execution.

- **discovery_type**: `ip_range` | `cidr` | `csv_import` | `controller_api` | `lldp_crawl`
- **discovery_config**: JSON (IP ranges, credentials, controller settings)
- **status**: `pending` | `running` | `completed` | `failed`
- **devices_discovered**: count
- **devices_created**: count (new Nautobot Device records)
- **devices_updated**: count (existing records updated)
- **errors**: JSON (devices that failed discovery, reasons)
- **run_timestamp**, **requested_by**

### `SessionRecord` (terminal session audit)

Represents a recorded terminal session for audit purposes.

- **device** (FK)
- **user** (FK to User)
- **session_start**, **session_end**
- **session_type**: `ssh` | `console` | `api`
- **commands_executed**: JSON array (command, timestamp, result)
- **session_log**: text blob (full session transcript, redacted)
- **status**: `active` | `completed` | `terminated`

### Git integration models

Option A (preferred): reuse Nautobot's existing Git integration primitives where possible.

- A model that maps a Git repository + path to Task/Workflow definitions.
- A model that records last import/export commit and status.

---

## Context schema (opinionated)

To keep Task Implementations reusable, we should standardize the Jinja2 context shape.

Recommended top-level keys:

- `device`: Nautobot Device (or a dict mirror in preview contexts)
- `interfaces`: list of interfaces (or `device.interfaces`)
- `vlans`, `vrfs`, `prefixes`, `ip_addresses`: optional collections (as needed)
- `intended`: intent payload supplied by the user/run (example below)
- `facts`: optional live facts gathered from device/controller
- `meta`: run metadata (requested_by, timestamp, etc.)

Example `intended` payload:

- `intended.port`:
  - mode: access|trunk
  - untagged_vlan: 123
  - tagged_vlans: [10, 20]
  - description: "User workstation"
- `intended.l3`:
  - vrf: "BLUE"
  - ip: "10.0.0.1/24"

This keeps templates predictable and supports both:

- “render-only” workflows
- “update Nautobot first, then render” workflows
