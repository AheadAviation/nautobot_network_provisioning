# Core objects (renamed for clarity)

## 1. Task Catalog (`TaskDefinition`)

A **Task** represents an abstract operation that can be performed on network devices. It's vendor/platform agnostic and defines "what" needs to be done.

**Examples**:
- "Change VLAN" - Change the VLAN assignment on an interface
- "Get Running Config" - Retrieve current running configuration
- "Save Config" - Persist running config to startup
- "Validate Interface State" - Check interface matches expected state
- "Create ServiceNow Ticket" - Create a change request in ServiceNow
- "Upgrade OS" - Perform software upgrade

**Key attributes**:
- **name**: Human-readable name (e.g., "Change VLAN")
- **slug**: URL-safe identifier (e.g., `change-vlan`)
- **description**: What this task does
- **category**: Grouping (e.g., "Configuration", "Validation", "ITSM", "Lifecycle")
- **input_schema**: JSON Schema defining required inputs (e.g., `interface`, `vlan_id`)
- **output_schema**: JSON Schema defining outputs (e.g., `success`, `before_config`, `after_config`)
- **tags**: For filtering/searching

## 2. Task Implementation (`TaskImplementation`)

A **Task Implementation** is a concrete, platform-specific way to execute a Task. One Task can have many implementations for different vendors/platforms.

**Key attributes**:
- **task** (FK): Which Task this implements
- **name**: Descriptive name (e.g., "Change VLAN - Cisco IOS-XE 17.x")
- **manufacturer** (FK to Manufacturer): e.g., Cisco
- **platform** (FK to Platform, optional): e.g., IOS-XE
- **software_version** (regex/range, optional): e.g., "17.*"
- **priority**: When multiple implementations match, use highest priority
- **implementation_type**:
  - `jinja2_config`: Render CLI commands
  - `jinja2_payload`: Render JSON/YAML for API
  - `api_call`: HTTP request
  - `graphql_query`: Query Nautobot
  - `python_hook`: Custom Python function (pro-code escape hatch)
- **template_content**: Jinja2 template (for template types)
- **action_config**: JSON config for API calls, hooks, etc.
- **pre_checks**: Validations to run before execution
- **post_checks**: Validations to run after execution

**Selection logic** (automatic):
```
Given: Device with Manufacturer=Cisco, Platform=IOS-XE, Software=17.3.4

1. Find all TaskImplementations for the requested Task
2. Filter by Manufacturer match (required)
3. Filter by Platform match (if specified)
4. Filter by Software version match (if specified, supports regex/range)
5. Select highest priority match
6. Fall back to "generic" implementation if no specific match
```

**UI flow for creating Task Implementation**:
1. Select Task (e.g., "Change VLAN")
2. Select Manufacturer (e.g., "Cisco") → filters available platforms
3. Select Platform (e.g., "IOS-XE") → filters available software versions
4. Optionally specify Software Version constraint
5. Choose implementation type (Jinja2 template, API call, etc.)
6. Write/paste template or configure action
7. Test against sample device

## 3. Workflow (`Workflow`)

A **Workflow** is an ordered sequence of Tasks that together accomplish a business objective. Workflows are what users actually execute.

**Key attributes**:
- **name**: Human-readable (e.g., "Change VLAN with Approval")
- **description**: What this workflow does end-to-end
- **category**: Grouping
- **steps**: Ordered list of workflow steps (see below)
- **input_schema**: Combined inputs needed from user/form
- **approval_required**: Whether this needs human approval
- **schedule_allowed**: Whether this can be scheduled for later

**Workflow Step types**:

1. **Task Step**: Execute a Task
   - References a TaskDefinition
   - Maps workflow context to task inputs
   - Captures task outputs to workflow context

2. **Validation Step**: Check conditions
   - Evaluate expressions (Jinja2 or simple conditions)
   - Fail workflow if validation fails
   - Can be "soft" (warn) or "hard" (stop)

3. **Approval Step**: Wait for human approval
   - Pause workflow execution
   - Notify approvers
   - Resume on approval, cancel on rejection
   - Supports external approval (webhook callback from ServiceNow, etc.)

4. **Notification Step**: Send notifications
   - Email, Slack, webhook
   - Template-based message content

5. **Condition Step**: Branch logic
   - If/else based on context values
   - Skip steps or take alternate paths

6. **Wait Step**: Scheduled delay
   - Wait for specific time
   - Wait for maintenance window
   - Wait for external callback (webhook)

**Example workflow definition**:
```yaml
name: "Change VLAN with Validation"
steps:
  - name: "Get Current Config"
    type: task
    task: get-running-config
    
  - name: "Validate Nautobot State"
    type: task
    task: validate-interface-state
    fail_on_mismatch: true
    
  - name: "Apply VLAN Change"
    type: task
    task: change-vlan
    inputs:
      interface: "{{ request.interface }}"
      vlan_id: "{{ request.new_vlan_id }}"
      
  - name: "Save Configuration"
    type: task
    task: save-config
    
  - name: "Verify Change"
    type: task
    task: validate-interface-state
    expected:
      vlan: "{{ request.new_vlan_id }}"
```

## 4. Request Form (`RequestForm`)

A **Request Form** is a user-facing form that exposes a Workflow to end users via the self-service portal.

**Key attributes**:
- **name**: Display name (e.g., "Change Interface VLAN")
- **description**: User-friendly explanation
- **workflow** (FK): Which workflow to execute
- **fields**: Ordered list of form fields (see below)
- **field_mapping**: How form fields map to workflow inputs
- **published**: Whether form is visible in portal
- **permissions**: Who can see/use this form

**Form field types**:
- **Object selector**: Pick a Device, Interface, VLAN, etc. from Nautobot
- **Text input**: Free-form text
- **Number input**: Integer or decimal
- **Choice**: Dropdown or radio buttons
- **Multi-choice**: Checkboxes or multi-select
- **Boolean**: Checkbox or toggle
- **Conditional**: Show/hide based on other field values

**Field configuration**:
- Label, help text, placeholder
- Required/optional
- Default value
- Validation rules (regex, range, etc.)
- Dynamic choices (queryset filters based on other selections)

## 5. Execution (`Execution`)

An **Execution** is a record of a workflow run—the full audit trail of what happened.

**Key attributes**:
- **workflow** (FK): Which workflow was executed
- **request_form** (FK, optional): Which form was used
- **requested_by**: User who initiated
- **approved_by**: User who approved (if applicable)
- **status**: pending / running / awaiting_approval / completed / failed / cancelled
- **inputs**: JSON snapshot of all inputs
- **context**: JSON of accumulated context during execution
- **step_results**: Per-step execution details
- **started_at**, **completed_at**
- **scheduled_for** (optional): If scheduled execution

**Step result details**:
- Step name
- Status (success/failed/skipped)
- Started/completed timestamps
- Rendered artifacts (config snippets, API payloads)
- Outputs
- Logs
- Error messages (if failed)

## 6. Provider (`Provider`)

A **Provider** is a driver that handles the actual communication with devices or external systems.

**Examples**:
- **Netmiko**: SSH CLI commands
- **NAPALM**: Multi-vendor abstraction
- **Scrapli**: SSH/Telnet CLI
- **RESTCONF**: REST API for network devices
- **DNAC API**: Cisco DNA Center
- **Meraki API**: Meraki Dashboard
- **ServiceNow API**: ITSM integration
- **HTTP/Webhook**: Generic API calls

**Key attributes**:
- **name**: Provider identifier
- **driver_class**: Python class that implements the provider interface
- **capabilities**: What this provider can do (connect, push_config, get_config, etc.)
- **supported_platforms**: Which platforms this provider works with

**ProviderConfig** (instance configuration):
- **provider** (FK): Which provider type
- **name**: Instance name (e.g., "Production DNAC", "Lab Meraki")
- **scope**: Site/Tenant/Tags this config applies to
- **credentials**: Reference to Nautobot Secrets
- **settings**: Provider-specific settings (timeouts, retries, base URLs)
