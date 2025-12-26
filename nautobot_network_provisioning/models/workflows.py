from django.db import models
from nautobot.core.models.generics import PrimaryModel
from .tasks import TaskIntent


class Workflow(PrimaryModel):
    """Orchestration of multiple TaskIntents into a business process."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)
    folder = models.ForeignKey(
        to='nautobot_network_provisioning.Folder',
        on_delete=models.SET_NULL,
        related_name='workflows',
        blank=True,
        null=True,
        help_text="Folder for organization in Catalog Explorer"
    )
    
    graph_definition = models.JSONField(
        blank=True, 
        null=True,
        help_text="Node-link structure (React Flow compatible) defining execution order."
    )
    
    enabled = models.BooleanField(default=True)
    approval_required = models.BooleanField(default=False)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class WorkflowStep(models.Model):
    """A specific step within a Workflow, linking to a TaskIntent."""

    workflow = models.ForeignKey(
        to=Workflow,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    task_intent = models.ForeignKey(
        to=TaskIntent,
        on_delete=models.PROTECT,
        related_name="workflow_steps",
    )
    weight = models.PositiveSmallIntegerField(default=100)
    parameters = models.JSONField(
        blank=True,
        null=True,
        help_text="Intent-specific parameters for this workflow step.",
    )

    class Meta:
        ordering = ("workflow", "weight", "task_intent")
        unique_together = (("workflow", "weight"),)

    def __str__(self):
        return f"{self.workflow} - Step {self.weight}: {self.task_intent}"
