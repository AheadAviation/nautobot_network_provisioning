# Summary

## Context

This repository currently provides a Nautobot app focused on **port provisioning** (templates + work queue + push) and **MAC tracking**. The next step is to evolve it into a **comprehensive network automation platform** that serves as the **automation and execution arm** of Nautobot.

**Key positioning**: We are the **automation/execution** platform. We integrate with other Nautobot apps that provide **data and tracking**:
- **Device Lifecycle Management** provides lifecycle tracking (EoL dates, maintenance contracts, CVE associations)
- **Golden Config** provides configuration backup/compliance tracking
- **This app** provides the automation workflows to execute changes, upgrades, onboarding, and remediation

## Goals

- **Low-code first, pro-code capable**
- **UI-first authoring**
- **GitOps-friendly**
- **Composable automation**: reusable **Tasks** + platform-specific **Implementations** assembled into **Workflows**
- **Nautobot-as-source-of-truth**: render from Nautobot data models + config context + relationships
- **Multi-vendor delivery** (CLI, controllers, render-only)
- **Safe operations** (preview/diff, approvals, audit trail)
- **Lifecycle automation**, **compliance automation**, **security/risk management**
- **Self-service portal** via Request Forms

## Non-goals

- Replace full orchestrators (Ansible Tower/AWX, NSO, proprietary NMS) in the first releases.
- Build a full topology solver or traffic engineering engine.
- Continuously reconcile drift on every device in real-time.

## Relationship to Golden Config

This app should **not** re-implement backup/config compliance engines. Instead:

- Use Golden Config as an optional “precheck gate” and/or informational link from Request Forms/Executions.
- Keep provisioning focused on: request intake, intent updates (SoT), rendering, execution via providers.

## Core concept hierarchy

```
Task Catalog (TaskDefinition)
  -> Task Implementations (TaskImplementation)
    -> Workflows
      -> Request Forms
        -> Executions (audit trail)
```

## Default “golden workflow”

Submit → Render → Preview/Diff → Approve (optional) → Execute → Record
