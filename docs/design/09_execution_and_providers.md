# Execution strategy and providers

## Execution strategy

### Render-only vs apply

Every Execution supports at least:

- `render`: produce artifacts deterministically and store in the Execution record

Providers may additionally support:

- `diff`: compute or retrieve a diff (CLI show diff, controller preview, etc.)
- `apply`: push config or call controller APIs

### Work queue + Jobs

Executions should be created and executed using existing patterns:

- Create an Execution record
- Execute asynchronously via Nautobot Jobs / Celery
- Update Execution status with progress messages and logs

This aligns with customer expectations for auditing and background execution.

---

## Provider abstraction (proposed Python interface)

Each provider implements something like:

- `validate_target(target)`
- `build_context(target, intended, meta)`
- `render(workflow, context)` (optional override; usually common render engine)
- `diff(target, rendered_artifacts, context)` (optional)
- `apply(target, rendered_artifacts, context)` (optional)

### DNAC example

DNAC often wants:

- intent modeled via controller objects
- templates/payloads pushed via DNAC APIs

So the DNAC provider may implement:

- `apply()` as “call DNAC to create/update object(s)”
- and optionally `render()` as payload templates (Jinja2 JSON)

### Meraki example

Meraki often wants:

- dashboard API calls per network

The Meraki provider may:

- map Nautobot Site/Tenant to Meraki Network ID
- apply VLANs/ports via API calls
