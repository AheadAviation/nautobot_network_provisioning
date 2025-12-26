import logging
from typing import Any, Optional
from django.utils import timezone
from nautobot.dcim.models import Device
from nautobot_network_provisioning.models import TaskIntent, Workflow, Execution, ExecutionStep, TaskStrategy
from .context_resolver import ContextResolver
from .template_renderer import build_context, render_template_from_context
from .provider_runtime import select_provider_config, load_provider_driver

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """
    The orchestration core (v2.0). 
    Handles variable resolution, implementation selection, and provider interaction.
    """

    def select_implementation(self, task_intent: TaskIntent, device: Device) -> Optional[TaskStrategy]:
        """Selection logic (Polymorphism). Finds the best match for the platform."""
        platform = device.platform
        if not platform:
            logger.warning(f"Device {device.name} has no platform. Cannot select strategy.")
            return None

        # Find strategies for this intent and platform
        strategy = TaskStrategy.objects.filter(
            task_intent=task_intent, 
            platform=platform, 
            enabled=True
        ).order_by("-priority").first()

        if not strategy:
            logger.error(f"No Strategy for Intent '{task_intent.slug}' on platform '{platform}'.")
            
        return strategy

    def execute_workflow(self, execution: Execution, target_obj: Any, dry_run: bool = False):
        """Runs the sequence of tasks defined in a workflow."""
        execution.status = "running"
        execution.save()

        try:
            # 1. Determine device context
            device = target_obj if isinstance(target_obj, Device) else getattr(target_obj, 'device', None)
            if not device:
                raise ValueError(f"Target object {target_obj} has no device context.")

            # 2. Setup Context Resolver
            # In v2.0, hierarchy is resolved per task or globally for the workflow
            # For now, we resolve globally based on execution inputs
            resolver = ContextResolver(device, overrides=execution.input_data or {})

            # 3. Select Provider
            provider_config = select_provider_config(device=device)
            if not provider_config:
                raise ValueError(f"No enabled AutomationProviderConfig found for {device}")
            
            driver = load_provider_driver(provider_config)

            # 4. Process Workflow Steps
            for step in execution.workflow.steps.all():
                task_intent = step.task_intent
                
                # A. Select Strategy (Polymorphism)
                strategy = self.select_implementation(task_intent, device)
                if not strategy:
                    raise Exception(f"Missing strategy for {task_intent.name} on {device.platform}")

                exec_step = ExecutionStep.objects.create(
                    execution=execution, 
                    task_strategy=strategy, 
                    status="running"
                )

                # B. Resolve Variables for this task
                # We fetch mappings from the intent
                mappings = task_intent.variable_mappings or []
                resolved = resolver.resolve(mappings)

                # C. Build Rendering Context
                render_ctx = build_context(
                    device=resolved["device"],
                    intended=resolved["intended"],
                    extra={
                        "config_context": resolved["config_context"],
                        "execution_id": str(execution.pk),
                        "meta": {"step": task_intent.name}
                    }
                )

                # D. Render & Execute
                if strategy.logic_type == "jinja2":
                    rendered = render_template_from_context(strategy.template_content, render_ctx)
                    exec_step.rendered_content = rendered
                    
                    if dry_run:
                        result = driver.diff(target=device, rendered_content=rendered, context=render_ctx)
                        exec_step.output = f"--- DIFF ---\n{result.diff}\n\n--- RENDERED ---\n{rendered}"
                    else:
                        result = driver.apply(target=device, rendered_content=rendered, context=render_ctx)
                        exec_step.output = f"--- LOGS ---\n{result.logs}\n\n--- RENDERED ---\n{rendered}"
                    
                    if not result.ok:
                        exec_step.status = "failed"
                        exec_step.error_message = result.details.get("error", "Unknown error")
                        exec_step.save()
                        raise Exception(f"Task {task_intent.name} failed: {exec_step.error_message}")

                exec_step.status = "completed"
                exec_step.end_time = timezone.now()
                exec_step.save()

            execution.status = "completed"
        except Exception as e:
            execution.status = "failed"
            logger.exception(f"Execution {execution.pk} failed")
        
        execution.end_time = timezone.now()
        execution.save()
