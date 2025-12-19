"""Phase 3: Request Forms and Portal models."""

from __future__ import annotations

from django.db import models
from nautobot.apps.models import PrimaryModel


class RequestForm(PrimaryModel):
    """User-facing form that exposes a Workflow in the self-service Portal."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=100, blank=True, help_text="Optional icon name (UI hint).")

    workflow = models.ForeignKey(
        to="nautobot_network_provisioning.Workflow",
        on_delete=models.PROTECT,
        related_name="request_forms",
    )

    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Request Form"
        verbose_name_plural = "Request Forms"

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class RequestFormField(PrimaryModel):
    """A single field in a RequestForm."""

    class FieldTypeChoices(models.TextChoices):
        OBJECT_SELECTOR = "object_selector", "Object Selector"
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        CHOICE = "choice", "Choice"
        MULTI_CHOICE = "multi_choice", "Multi Choice"
        BOOLEAN = "boolean", "Boolean"

    form = models.ForeignKey(to=RequestForm, on_delete=models.CASCADE, related_name="fields")
    order = models.PositiveIntegerField(default=0, db_index=True)

    field_name = models.CharField(
        max_length=100,
        help_text="Internal name; also used as the key in Execution.inputs by default.",
    )
    field_type = models.CharField(max_length=24, choices=FieldTypeChoices.choices)

    label = models.CharField(max_length=150)
    help_text = models.TextField(blank=True)
    required = models.BooleanField(default=False)

    default_value = models.JSONField(default=dict, blank=True)
    validation_rules = models.JSONField(default=dict, blank=True)

    choices = models.JSONField(default=list, blank=True, help_text="For choice/multi_choice fields.")

    object_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="For object selectors: the target object type (e.g., dcim.device).",
    )
    queryset_filter = models.JSONField(default=dict, blank=True, help_text="Optional queryset filter (JSON).")

    # High-level lookup helpers for "Low Code" usage
    class LookupTypeChoices(models.TextChoices):
        MANUAL = "manual", "Manual JSON Filter"
        LOCATION_BY_TYPE = "location_by_type", "Location by Type"
        VLAN_BY_TAG = "vlan_by_tag", "VLAN by Tag"
        DEVICE_BY_ROLE = "device_by_role", "Device by Role"
        TASK_BY_CATEGORY = "task_by_category", "Task by Category"

    lookup_type = models.CharField(
        max_length=32,
        choices=LookupTypeChoices.choices,
        default=LookupTypeChoices.MANUAL,
        help_text="Simplified lookup logic for this field."
    )
    lookup_config = models.JSONField(default=dict, blank=True, help_text="Configuration for the simplified lookup.")

    depends_on = models.ForeignKey(
        to="self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependents",
    )
    show_condition = models.TextField(blank=True, help_text="Jinja2 expression for conditional visibility.")

    # Optional: explicitly map to a key in workflow/execution inputs.
    map_to = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional dotted path to map into Execution.inputs (defaults to field_name).",
    )

    class Meta:
        ordering = ["form__name", "order", "field_name"]
        constraints = [
            models.UniqueConstraint(fields=["form", "order"], name="uniq_requestformfield_form_order"),
            models.UniqueConstraint(fields=["form", "field_name"], name="uniq_requestformfield_form_field_name"),
        ]
        verbose_name = "Request Form Field"
        verbose_name_plural = "Request Form Fields"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.form.name}: {self.field_name}"


