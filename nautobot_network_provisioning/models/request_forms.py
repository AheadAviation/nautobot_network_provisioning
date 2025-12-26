from django.db import models
from django.contrib.contenttypes.models import ContentType
from nautobot.core.models.generics import PrimaryModel
from .workflows import Workflow


class RequestForm(PrimaryModel):
    """User-facing portal interface for triggering Workflows (The Front Door)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    workflow = models.ForeignKey(
        to=Workflow,
        on_delete=models.PROTECT,
        related_name="request_forms",
    )
    description = models.CharField(max_length=200, blank=True)
    folder = models.ForeignKey(
        to='nautobot_network_provisioning.Folder',
        on_delete=models.SET_NULL,
        related_name='forms',
        blank=True,
        null=True,
        help_text="Folder for organization in Catalog Explorer"
    )
    published = models.BooleanField(default=True)
    
    field_definition = models.JSONField(
        blank=True,
        null=True,
        help_text="Mapping of form fields to Workflow/Intent variables."
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class RequestFormField(models.Model):
    """
    Specific field definition for a RequestForm. 
    Note: In v2.0, this may be deprecated in favor of field_definition JSON, 
    but kept for backwards compatibility or more granular control if needed.
    """

    form = models.ForeignKey(
        to=RequestForm,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    field_name = models.CharField(max_length=100)
    label = models.CharField(max_length=100, blank=True)
    field_type = models.CharField(
        max_length=50,
        choices=(
            ("text", "Text"),
            ("number", "Number"),
            ("boolean", "Boolean"),
            ("choice", "Choice"),
            ("multi_choice", "Multi-Choice"),
            ("object_selector", "Object Selector (Nautobot Model)"),
        ),
        default="text",
    )
    object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text="Required for object_selector field type.",
    )
    choices = models.JSONField(
        blank=True,
        null=True,
        help_text="List of choices for choice/multi_choice types.",
    )
    required = models.BooleanField(default=True)
    default = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=100)

    # Advanced Logic
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="dependents",
    )
    show_condition = models.CharField(
        max_length=200,
        blank=True,
        help_text="Jinja2 expression for conditional visibility (e.g. 'input.role == \"access\"').",
    )
    map_to = models.CharField(
        max_length=100,
        blank=True,
        help_text="Dotted path to map this input to in the execution context (e.g. 'vars.vlan_id').",
    )
    sot_loopback = models.BooleanField(
        default=False,
        help_text="If true, this field will update a Nautobot model attribute during execution.",
    )
    sot_path = models.CharField(
        max_length=100,
        blank=True,
        help_text="Dotted path to the model attribute (e.g. 'interface.description' or 'device.location').",
    )

    class Meta:
        ordering = ("form", "order", "field_name")
        unique_together = (("form", "field_name"),)

    def __str__(self):
        return f"{self.form.name} - {self.field_name}"
