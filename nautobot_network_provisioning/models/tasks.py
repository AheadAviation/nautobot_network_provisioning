"""Task catalog and platform-specific implementations."""

from __future__ import annotations

from django.db import models
from nautobot.apps.models import PrimaryModel


class TaskDefinition(PrimaryModel):
    """Vendor-agnostic task ("what to do")."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    input_schema = models.JSONField(default=dict, blank=True)
    output_schema = models.JSONField(default=dict, blank=True)
    documentation = models.TextField(blank=True, help_text="Markdown help text.")

    natural_key_field_names = ["slug"]

    class Meta:
        ordering = ["name"]
        verbose_name = "Task"
        verbose_name_plural = "Task Catalog"

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class TaskImplementation(PrimaryModel):
    """Platform-specific implementation ("how to do it")."""

    class ImplementationTypeChoices(models.TextChoices):
        JINJA2_CONFIG = "jinja2_config", "Jinja2 Config"
        JINJA2_PAYLOAD = "jinja2_payload", "Jinja2 Payload"
        API_CALL = "api_call", "API Call"
        GRAPHQL_QUERY = "graphql_query", "GraphQL Query"
        PYTHON_HOOK = "python_hook", "Python Hook"

    task = models.ForeignKey(to=TaskDefinition, on_delete=models.PROTECT, related_name="implementations")
    name = models.CharField(max_length=150)

    manufacturer = models.ForeignKey(to="dcim.Manufacturer", on_delete=models.PROTECT, related_name="task_implementations")
    platform = models.ForeignKey(
        to="dcim.Platform",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_implementations",
    )
    software_versions = models.ManyToManyField(
        to="dcim.SoftwareVersion",
        blank=True,
        related_name="task_implementations",
        help_text="Optional: restrict this implementation to specific SoftwareVersion records. Leave empty for all versions.",
    )
    priority = models.IntegerField(default=100, help_text="Higher wins when multiple implementations match.")

    implementation_type = models.CharField(max_length=32, choices=ImplementationTypeChoices.choices)
    template_content = models.TextField(blank=True, help_text="Jinja2 template or query text (for template-based types).")
    action_config = models.JSONField(default=dict, blank=True, help_text="Config for API calls, hooks, etc.")
    pre_checks = models.JSONField(default=list, blank=True)
    post_checks = models.JSONField(default=list, blank=True)

    provider_config = models.ForeignKey(
        to="nautobot_network_provisioning.ProviderConfig",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_implementations",
        help_text="Optional override of provider selection for this implementation.",
    )

    enabled = models.BooleanField(default=True)

    natural_key_field_names = ["task", "manufacturer", "platform", "name"]

    class Meta:
        ordering = ["task__name", "-priority", "name"]
        verbose_name = "Task Implementation"
        verbose_name_plural = "Task Implementations"

    def __str__(self) -> str:  # pragma: no cover
        return self.name


