"""Workflow orchestration models."""

from __future__ import annotations

from django.db import models
from nautobot.apps.models import PrimaryModel


class Workflow(PrimaryModel):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=50, blank=True, help_text="Optional semantic version.")
    enabled = models.BooleanField(default=True)

    approval_required = models.BooleanField(default=False)
    schedule_allowed = models.BooleanField(default=False)

    input_schema = models.JSONField(default=dict, blank=True)
    default_inputs = models.JSONField(default=dict, blank=True)

    natural_key_field_names = ["slug"]

    class Meta:
        ordering = ["name"]
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class WorkflowStep(PrimaryModel):
    class StepTypeChoices(models.TextChoices):
        TASK = "task", "Task"
        VALIDATION = "validation", "Validation"
        APPROVAL = "approval", "Approval"
        NOTIFICATION = "notification", "Notification"
        CONDITION = "condition", "Condition"
        WAIT = "wait", "Wait"

    class OnFailureChoices(models.TextChoices):
        STOP = "stop", "Stop"
        CONTINUE = "continue", "Continue"
        SKIP_REMAINING = "skip_remaining", "Skip Remaining"

    workflow = models.ForeignKey(to=Workflow, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField(default=0, db_index=True)
    name = models.CharField(max_length=150)

    step_type = models.CharField(max_length=24, choices=StepTypeChoices.choices)

    task = models.ForeignKey(
        to="nautobot_network_provisioning.TaskDefinition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_steps",
    )
    input_mapping = models.JSONField(default=dict, blank=True)
    output_mapping = models.JSONField(default=dict, blank=True)
    condition = models.TextField(blank=True, help_text="Jinja2 expression to determine whether this step runs.")
    on_failure = models.CharField(max_length=24, choices=OnFailureChoices.choices, default=OnFailureChoices.STOP)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["workflow__name", "order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["workflow", "order"], name="uniq_workflowstep_workflow_order"),
        ]
        verbose_name = "Workflow Step"
        verbose_name_plural = "Workflow Steps"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.workflow.name}: {self.order} - {self.name}"


