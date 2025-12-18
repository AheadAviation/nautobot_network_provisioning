# Core concepts and flows

## Core concepts

### Design philosophy: Low-code first, pro-code capable

This platform is designed for **two audiences**:

1. **Low-code users** (network engineers, operators): Build and execute automation using the UI without writing code
2. **Pro-code users** (automation engineers, developers): Extend the platform with custom Python hooks, integrations, and advanced logic

Everything should be achievable via the UI first. Code is an escape hatch for advanced use cases, not a requirement.

### Source of truth vs. delivery

- **Source of truth**: Nautobot models + config context + custom fields + relationships.
- **Delivery**: multiple execution targets (device CLI, controller API, render-only artifacts).

---

## Concept hierarchy and flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONCEPT HIERARCHY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  TASK CATALOG   │  "What operations exist?" (e.g., Change VLAN)           │
│  │                 │  - Abstract definition of an operation                  │
│  │                 │  - Vendor/platform agnostic                             │
│  └────────┬────────┘                                                         │
│           │ has many                                                         │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │ TASK IMPLEMEN-  │  "How do I do it on this platform?"                     │
│  │ TATIONS         │  - Manufacturer → Platform → Software Version           │
│  │                 │  - Contains Jinja2 templates, API calls, scripts        │
│  │                 │  - Multiple implementations per Task                    │
│  └────────┬────────┘                                                         │
│           │ used in                                                          │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │   WORKFLOWS     │  "What's the end-to-end process?"                       │
│  │                 │  - Ordered sequence of Tasks                            │
│  │                 │  - Includes validation, approvals, notifications        │
│  │                 │  - Can integrate with ITSM (ServiceNow, etc.)           │
│  └────────┬────────┘                                                         │
│           │ exposed via                                                      │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │  REQUEST FORMS  │  "How do users request this?"                           │
│  │                 │  - User-facing form with guided inputs                  │
│  │                 │  - Published to portal for self-service                 │
│  │                 │  - Maps form fields to workflow inputs                  │
│  └────────┬────────┘                                                         │
│           │ creates                                                          │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │   EXECUTIONS    │  "What happened when it ran?"                           │
│  │                 │  - Audit trail of every run                             │
│  │                 │  - Logs, diffs, results, approvals                      │
│  └─────────────────┘                                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## End-to-end flow diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXAMPLE: CHANGE VLAN WORKFLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER SUBMITS REQUEST                                                        │
│  ════════════════════                                                        │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ Request Form │───▶│  Workflow    │───▶│  Execution   │                   │
│  │ "Change VLAN"│    │  Engine      │    │  Record      │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   │                                                │
│         ▼                   ▼                                                │
│  Form inputs:          Workflow steps:                                       │
│  - Device              1. Validate inputs                                    │
│  - Interface           2. Pull current config (Task: Get Config)             │
│  - New VLAN ID         3. Validate against Nautobot (Task: Validate State)   │
│                        4. Create ITSM ticket (Task: ServiceNow Create)       │
│                        5. Wait for approval (webhook callback)               │
│                        6. Execute change (Task: Change VLAN)                 │
│                        7. Write memory (Task: Save Config)                   │
│                        8. Validate change (Task: Validate State)             │
│                        9. Close ITSM ticket (Task: ServiceNow Update)        │
│                        10. Notify user                                       │
│                                                                              │
│  TASK RESOLUTION                                                             │
│  ═══════════════                                                             │
│                                                                              │
│  Step 6: "Change VLAN"                                                       │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────┐                                │
│  │ Task: Change VLAN                        │                                │
│  │ Description: Change VLAN on interface    │                                │
│  └─────────────────────────────────────────┘                                │
│         │                                                                    │
│         │ Select implementation based on device:                             │
│         │ Manufacturer: Cisco                                                │
│         │ Platform: IOS-XE                                                   │
│         │ Software: 17.x                                                     │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────┐                                │
│  │ Task Implementation: change_vlan_ios_xe │                                │
│  │ Template:                                │                                │
│  │   interface {{ interface.name }}         │                                │
│  │   switchport access vlan {{ vlan_id }}   │                                │
│  └─────────────────────────────────────────┘                                │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────┐                                │
│  │ Provider: Netmiko (CLI push)             │                                │
│  │ - Connect to device                      │                                │
│  │ - Send rendered config                   │                                │
│  │ - Return result                          │                                │
│  └─────────────────────────────────────────┘                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MVP Workflow example

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MVP WORKFLOW: SIMPLE VLAN CHANGE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────┐    ┌───────┐    ┌───────┐    ┌───────┐    ┌───────┐             │
│  │ Pull  │───▶│Validate│───▶│Change │───▶│ Save  │───▶│Validate│            │
│  │Config │    │ State │    │ VLAN  │    │Config │    │ Task  │             │
│  └───────┘    └───────┘    └───────┘    └───────┘    └───────┘             │
│                                                                              │
│  Step 1: Pull current running config from device                            │
│  Step 2: Validate interface state matches Nautobot data                     │
│  Step 3: Apply VLAN change to interface                                     │
│  Step 4: Write memory / copy run start                                      │
│  Step 5: Validate the change was applied successfully                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```
