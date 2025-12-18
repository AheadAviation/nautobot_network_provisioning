# Self-Service Portal (Request Forms)

## Problem with current request page

The existing "New Request" (`port-config-request`) works for one fixed workflow, but it is not:

- Customizable per customer/team
- Scalable to "all workflows"
- Friendly for low-skill requesters
- A good fit for approvals and pipeline-style automation

## Goal

Provide a **self-service portal** where operators can request *any* workflow using **custom, UI-defined request forms**, with built-in validation, approval, and execution.

## UX: One portal, many workflows

**Automation → Portal**

- Browse available Request Forms (e.g., "Change VLAN", "Add Trunk Port", "Create VLAN", "Upgrade Device")
- Select a form → fill in the fields (guided, with validation)
- Preview (what will change, what will be pushed)
- Submit → creates an Execution record
- Track status (Submitted → Awaiting Approval → Running → Completed/Failed)

This portal is intentionally the "front door" for day-2 operations: users don't need to understand Tasks or Workflows—just fill in forms and get work done.

## Request Form design principles

**Low-code users** should be able to:
- Create forms entirely in the UI
- Use drag-and-drop field ordering
- Set up conditional logic without code
- Preview and test forms before publishing

**Pro-code users** can additionally:
- Define custom validation logic (Python hooks)
- Create dynamic field choices via GraphQL queries
- Extend forms with custom field types

## Form → Workflow mapping

Each Request Form links to exactly **one Workflow**. The form fields map to the workflow's input schema:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REQUEST FORM → WORKFLOW MAPPING                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Request Form: "Change Interface VLAN"                                       │
│  ┌─────────────────────────────────────┐                                    │
│  │ Field: device (Object Selector)     │──────┐                             │
│  │ Field: interface (Object Selector)  │──────┤                             │
│  │ Field: new_vlan_id (Number)         │──────┤   Maps to                   │
│  │ Field: description (Text, optional) │──────┤   ─────────▶                │
│  └─────────────────────────────────────┘      │                             │
│                                               │                             │
│                                               ▼                             │
│  Workflow: "Change VLAN with Validation"                                     │
│  ┌─────────────────────────────────────┐                                    │
│  │ Input: device (Device)              │                                    │
│  │ Input: interface (Interface)        │                                    │
│  │ Input: new_vlan_id (Integer)        │                                    │
│  │ Input: description (String)         │                                    │
│  └─────────────────────────────────────┘                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Variable sources in Workflows

Workflows can access variables from multiple sources:

1. **Form inputs**: Values submitted by the user (e.g., `input.device`, `input.new_vlan_id`)
2. **Nautobot context**: Data fetched from Nautobot via GraphQL or ORM (e.g., `device.interfaces`, `device.platform`)
3. **Task outputs**: Results from previous steps (e.g., `steps.get_config.output.running_config`)
4. **External data**: API responses, webhook payloads, etc.

## Workflow step types (n8n-like, but network-focused)

Workflows are composed of ordered steps. Step types:

1. **Task**: Execute a Task (resolves to platform-specific implementation)
2. **Validation**: Check conditions, fail or warn
3. **Approval**: Pause for human approval (in-app or via webhook from ITSM)
4. **Notification**: Send email, Slack, webhook
5. **Condition**: If/else branching
6. **Wait**: Delay execution (schedule, maintenance window, callback)

## RBAC and roles

We should formalize three roles (implemented via Nautobot Groups + ObjectPermissions):

- **Requester**
  - Can view the portal and submit requests
  - Can view only their own requests (or scoped requests)

- **Approver**
  - Can view/approve/reject requests within scope
  - Can see diffs/preview artifacts, logs

- **Form Builder (Designer)**
  - Can create/edit request form definitions and pipelines
  - Can publish/unpublish forms

Optional fourth role:

- **Operator**
  - Can execute/force-run requests (break-glass), view all logs

## “Portal-only” user experience

We can get close to “portal-only” without trying to hide core Nautobot:

- Provide a dedicated landing page URL for the Request Portal.
- Ensure Requester users have permissions only for:
  - the portal view
  - creating Request objects
  - reading their own Request objects
- Hide navigation items from users without permissions (standard Nautobot behavior).

## Data model additions (proposed)

- `RequestFormDefinition`
  - metadata + field schema
  - pipeline reference
  - publish flag + scoping

- `Request`
  - requester, timestamps
  - selected form + inputs (JSON)
  - resolved targets (FKs)
  - status + approval metadata
  - rendered artifacts + diffs + provider results

> Note: Phase 3+ item; Phase 1/2 focus is Task/Workflow/Execution.
  - ordered stages (v1) or node graph (v2)
  - per-stage config
