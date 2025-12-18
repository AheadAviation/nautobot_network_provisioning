"""Execution engine (Phases 2-5).

Phase 2: render-only workflow execution for auditability.
Phase 4: provider abstraction for diff/apply.
Phase 5: approval step pauses execution until approved.
"""

from __future__ import annotations

from django.utils import timezone

from nautobot_network_provisioning.models import Execution, ExecutionStep, WorkflowStep
from nautobot_network_provisioning.services.implementation_selector import select_task_implementation
from nautobot_network_provisioning.services.provider_runtime import (
    ProviderError,
    ProviderOperationNotSupported,
    load_provider_driver,
    select_provider_config,
)
from nautobot_network_provisioning.services.template_renderer import build_context, render_template_from_context


def _native_napalm_operation(*, device, rendered_content: str, operation: str):  # noqa: ANN001
    """Run diff/apply using Nautobot-native NAPALM connectivity (Device.get_napalm_device()) if available."""

    get_napalm = getattr(device, "get_napalm_device", None)
    if not callable(get_napalm):
        raise ProviderError("No ProviderConfig matched and device has no get_napalm_device(); configure a ProviderConfig.")

    napalm_device = get_napalm()
    try:
        napalm_device.open()
        napalm_device.load_merge_candidate(config=rendered_content or "")
        diff = napalm_device.compare_config() or ""
        if operation == "diff":
            napalm_device.discard_config()
            return {"ok": True, "details": {"diff": diff}, "logs": "Native NAPALM diff complete."}
        napalm_device.commit_config()
        return {"ok": True, "details": {"diff": diff, "committed": True}, "logs": "Native NAPALM apply complete."}
    except Exception as e:  # noqa: BLE001
        try:
            napalm_device.discard_config()
        except Exception:  # noqa: BLE001
            pass
        return {"ok": False, "details": {"error": str(e)}, "logs": "Native NAPALM operation failed."}
    finally:
        try:
            napalm_device.close()
        except Exception:  # noqa: BLE001
            pass


def run_execution(execution: Execution, *, operation: str = "render") -> Execution:
    """Execute a workflow.

    operation:
    - render: render artifacts only
    - diff: render + provider diff where supported
    - apply: render + provider apply where supported
    """

    if operation not in {"render", "diff", "apply"}:
        raise ValueError("operation must be one of: render, diff, apply")

    if execution.status not in {Execution.StatusChoices.PENDING, Execution.StatusChoices.SCHEDULED}:
        return execution

    execution.status = Execution.StatusChoices.RUNNING
    execution.started_at = timezone.now()
    execution.save(update_fields=["status", "started_at", "last_updated"])

    # Very small v1 target model: use first device only for matching/context.
    device = execution.target_devices.first()
    manufacturer = getattr(getattr(device, "device_type", None), "manufacturer", None) if device else None
    platform = getattr(device, "platform", None) if device else None
    software_version = getattr(device, "software_version", None) if device else None

    ctx = build_context(
        device=device,
        interfaces=None,
        intended={"inputs": execution.inputs or {}},
        meta={"execution_id": str(execution.pk)},
    )
    execution.context = ctx
    execution.save(update_fields=["context", "last_updated"])

    steps = WorkflowStep.objects.filter(workflow=execution.workflow).order_by("order", "name")
    order = 0
    try:
        for step in steps:
            order += 1
            es, created = ExecutionStep.objects.get_or_create(
                execution=execution,
                order=order,
                defaults={
                    "workflow_step": step,
                    "status": ExecutionStep.StatusChoices.RUNNING,
                    "started_at": timezone.now(),
                    "inputs": {},
                    "outputs": {},
                },
            )
            if not created and es.status in {ExecutionStep.StatusChoices.COMPLETED, ExecutionStep.StatusChoices.SKIPPED}:
                # Idempotency/resume: skip already completed steps.
                continue
            if not created:
                # Keep linkage in case workflow was edited.
                es.workflow_step = step
                es.status = ExecutionStep.StatusChoices.RUNNING
                es.started_at = es.started_at or timezone.now()
                es.save(update_fields=["workflow_step", "status", "started_at", "last_updated"])

            # Step type handlers
            if step.step_type == WorkflowStep.StepTypeChoices.APPROVAL:
                # Pause execution until approved.
                if not execution.approved_by_id:
                    es.logs = (es.logs or "") + "\nAwaiting approval."
                    es.save(update_fields=["logs", "last_updated"])
                    execution.status = Execution.StatusChoices.AWAITING_APPROVAL
                    execution.save(update_fields=["status", "last_updated"])
                    return execution

                es.status = ExecutionStep.StatusChoices.COMPLETED
                es.completed_at = timezone.now()
                es.logs = (es.logs or "") + "\nApproved; continuing."
                es.save(update_fields=["status", "completed_at", "logs", "last_updated"])
                continue

            if step.step_type != WorkflowStep.StepTypeChoices.TASK or not step.task:
                es.status = ExecutionStep.StatusChoices.SKIPPED
                es.completed_at = timezone.now()
                es.save(update_fields=["status", "completed_at", "last_updated"])
                continue

            if not manufacturer:
                raise ValueError("Cannot select implementation: target device manufacturer is unknown.")

            impl = select_task_implementation(
                task=step.task,
                manufacturer=manufacturer,
                platform=platform,
                software_version=software_version,
            )
            if not impl:
                raise ValueError(f"No matching TaskImplementation found for task '{step.task.slug}'.")

            es.task_implementation = impl

            rendered = ""
            if impl.implementation_type in {
                impl.ImplementationTypeChoices.JINJA2_CONFIG,
                impl.ImplementationTypeChoices.JINJA2_PAYLOAD,
            }:
                rendered = render_template_from_context(impl.template_content or "", ctx)
            else:
                rendered = ""

            es.rendered_content = rendered

            # Provider operations
            if operation in {"diff", "apply"}:
                provider_config = impl.provider_config or select_provider_config(device=device)
                driver = None
                if provider_config:
                    driver = load_provider_driver(provider_config)
                    driver.validate_target(target=device)

                if operation == "diff":
                    try:
                        if driver:
                            result = driver.diff(target=device, rendered_content=rendered, context=ctx)
                            es.outputs = {
                                **(es.outputs or {}),
                                "provider": provider_config.name,
                                "diff": result.details.get("diff", ""),
                                "details": result.details,
                            }
                            es.logs = (es.logs or "") + "\n" + (result.logs or "")
                        else:
                            native = _native_napalm_operation(device=device, rendered_content=rendered, operation="diff")
                            es.outputs = {
                                **(es.outputs or {}),
                                "provider": "nautobot_napalm",
                                "diff": native["details"].get("diff", ""),
                                "details": native["details"],
                            }
                            es.logs = (es.logs or "") + "\n" + (native.get("logs") or "")
                    except ProviderOperationNotSupported as e:
                        es.outputs = {
                            **(es.outputs or {}),
                            "provider": provider_config.name if provider_config else "nautobot_napalm",
                            "diff": "",
                            "details": {"error": str(e)},
                        }
                        es.logs = (es.logs or "") + f"\nProvider diff not supported: {e}"
                else:  # apply
                    try:
                        if driver:
                            result = driver.apply(target=device, rendered_content=rendered, context=ctx)
                            es.outputs = {**(es.outputs or {}), "provider": provider_config.name, "details": result.details}
                            if "diff" in result.details:
                                es.outputs["diff"] = result.details.get("diff")
                            es.logs = (es.logs or "") + "\n" + (result.logs or "")
                            if not result.ok:
                                raise ProviderError(result.details.get("error") or "Provider apply failed.")
                        else:
                            native = _native_napalm_operation(device=device, rendered_content=rendered, operation="apply")
                            es.outputs = {
                                **(es.outputs or {}),
                                "provider": "nautobot_napalm",
                                "details": native["details"],
                                "diff": native["details"].get("diff", ""),
                            }
                            es.logs = (es.logs or "") + "\n" + (native.get("logs") or "")
                            if not native["ok"]:
                                raise ProviderError(native["details"].get("error") or "Native NAPALM apply failed.")
                    except ProviderOperationNotSupported as e:
                        raise ProviderError(f"Provider apply not supported: {e}") from e

            es.status = ExecutionStep.StatusChoices.COMPLETED
            es.completed_at = timezone.now()
            es.save(
                update_fields=[
                    "task_implementation",
                    "rendered_content",
                    "outputs",
                    "logs",
                    "status",
                    "completed_at",
                    "last_updated",
                ]
            )

        execution.status = Execution.StatusChoices.COMPLETED
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "completed_at", "last_updated"])
        return execution
    except Exception as e:  # noqa: BLE001
        execution.status = Execution.StatusChoices.FAILED
        execution.completed_at = timezone.now()
        execution.context = {**(execution.context or {}), "error": str(e)}
        execution.save(update_fields=["status", "completed_at", "context", "last_updated"])
        return execution


def render_execution(execution: Execution) -> Execution:
    """Backward-compatible wrapper (Phase 2)."""

    return run_execution(execution, operation="render")


