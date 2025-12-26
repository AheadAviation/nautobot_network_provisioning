from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from nautobot.core.models.generics import PrimaryModel
from nautobot.apps.models import StatusField
from .workflows import Workflow
from .request_forms import RequestForm
from .tasks import TaskStrategy

User = get_user_model()


class Execution(PrimaryModel):
    """The audit trail - record of a Workflow execution."""

    workflow = models.ForeignKey(
        to=Workflow,
        on_delete=models.PROTECT,
        related_name="executions",
    )
    request_form = models.ForeignKey(
        to=RequestForm,
        on_delete=models.SET_NULL,
        related_name="executions",
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.PROTECT,
        related_name="executions",
    )
    # Generic foreign key to the target object (Device, Interface, etc.)
    object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        related_name="+",
        blank=True,
        null=True,
    )
    object_id = models.UUIDField(blank=True, null=True)
    target_object = GenericForeignKey("object_type", "object_id")

    # Using Nautobot's StatusField for state management
    status = StatusField(related_name="executions")
    input_data = models.JSONField(
        blank=True,
        null=True,
        help_text="The inputs provided at the time of execution.",
    )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-start_time",)

    def __str__(self):
        return f"Execution {self.pk} - {self.workflow} ({self.status})"


class ExecutionStep(models.Model):
    """A record of a specific TaskStrategy execution within an Execution."""

    execution = models.ForeignKey(
        to=Execution,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    task_strategy = models.ForeignKey(
        to=TaskStrategy,
        on_delete=models.PROTECT,
        related_name="execution_steps",
    )
    status = StatusField(related_name="execution_steps")
    rendered_content = models.TextField(blank=True, help_text="The rendered config or payload.")
    output = models.TextField(blank=True, help_text="Actual output from the device/provider.")
    error_message = models.TextField(blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("execution", "start_time")

    def __str__(self):
        return f"{self.execution} - {self.task_strategy} ({self.status})"
