"""Execution/audit trail models for workflow runs."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from nautobot.apps.models import PrimaryModel


class Execution(PrimaryModel):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    workflow = models.ForeignKey(to="nautobot_network_provisioning.Workflow", on_delete=models.PROTECT, related_name="executions")

    requested_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="automation_executions",
    )
    approved_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="automation_executions_approved",
    )

    status = models.CharField(max_length=32, choices=StatusChoices.choices, default=StatusChoices.PENDING, db_index=True)

    inputs = models.JSONField(default=dict, blank=True)
    context = models.JSONField(default=dict, blank=True)

    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    target_devices = models.ManyToManyField(to="dcim.Device", blank=True, related_name="automation_executions")

    class Meta:
        ordering = ["-created"]
        verbose_name = "Execution"
        verbose_name_plural = "Executions"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.workflow.name} ({self.status})"


class ExecutionStep(PrimaryModel):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    execution = models.ForeignKey(to=Execution, on_delete=models.CASCADE, related_name="steps")
    workflow_step = models.ForeignKey(
        to="nautobot_network_provisioning.WorkflowStep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="execution_steps",
    )
    order = models.PositiveIntegerField(default=0, db_index=True)

    status = models.CharField(max_length=24, choices=StatusChoices.choices, default=StatusChoices.PENDING, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    task_implementation = models.ForeignKey(
        to="nautobot_network_provisioning.TaskImplementation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="execution_steps",
    )

    rendered_content = models.TextField(blank=True)
    inputs = models.JSONField(default=dict, blank=True)
    outputs = models.JSONField(default=dict, blank=True)
    logs = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["execution__created", "order"]
        constraints = [
            models.UniqueConstraint(fields=["execution", "order"], name="uniq_executionstep_execution_order"),
        ]
        verbose_name = "Execution Step"
        verbose_name_plural = "Execution Steps"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.execution_id}: {self.order}"


