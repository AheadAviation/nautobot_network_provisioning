"""Forms for the Network Provisioning (Automation) app."""

from __future__ import annotations

from django import forms
from django.contrib.contenttypes.models import ContentType
from nautobot.apps.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    TagFilterField,
)
from nautobot.dcim.models import Manufacturer, Platform, SoftwareVersion, Location
from nautobot.extras.models import SecretsGroup, Tag
from nautobot.tenancy.models import Tenant

from nautobot_network_provisioning.models import (
    Execution,
    Provider,
    ProviderConfig,
    RequestForm,
    RequestFormField,
    TaskDefinition,
    TaskImplementation,
    Workflow,
    WorkflowStep,
)
from nautobot_network_provisioning.widgets import Jinja2EditorWidget


# =============================================================================
# Task Catalog (TaskDefinition)
# =============================================================================


class TaskDefinitionForm(NautobotModelForm):
    class Meta:
        model = TaskDefinition
        fields = ["name", "slug", "description", "category", "input_schema", "output_schema", "documentation", "tags"]


class TaskDefinitionBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=TaskDefinition.objects.all(), widget=forms.MultipleHiddenInput())
    category = forms.CharField(required=False)

    class Meta:
        model = TaskDefinition
        nullable_fields = ["description", "category", "documentation"]


class TaskDefinitionFilterForm(NautobotFilterForm):
    model = TaskDefinition
    q = forms.CharField(required=False, label="Search")
    category = forms.CharField(required=False)
    tags = TagFilterField(model)


# =============================================================================
# Task Implementations (TaskImplementation)
# =============================================================================


class TaskImplementationForm(NautobotModelForm):
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=True)
    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        query_params={"manufacturer_id": "$manufacturer"},
    )
    provider_config = DynamicModelChoiceField(queryset=ProviderConfig.objects.all(), required=False)
    software_versions = DynamicModelMultipleChoiceField(
        queryset=SoftwareVersion.objects.all(),
        required=False,
        query_params={"platform_id": "$platform"},
        help_text="Optional: restrict to specific SoftwareVersion records; leave empty for all versions.",
    )

    class Meta:
        model = TaskImplementation
        fields = [
            "task",
            "name",
            "manufacturer",
            "platform",
            "software_versions",
            "priority",
            "implementation_type",
            "template_content",
            "action_config",
            "pre_checks",
            "post_checks",
            "provider_config",
            "enabled",
            "tags",
        ]
        widgets = {
            "template_content": Jinja2EditorWidget(),
            "action_config": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "pre_checks": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "post_checks": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
        }


class TaskImplementationBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=TaskImplementation.objects.all(), widget=forms.MultipleHiddenInput())
    enabled = forms.NullBooleanField(required=False)
    priority = forms.IntegerField(required=False)
    implementation_type = forms.ChoiceField(choices=TaskImplementation.ImplementationTypeChoices.choices, required=False)

    class Meta:
        model = TaskImplementation
        nullable_fields = ["platform", "provider_config"]


class TaskImplementationFilterForm(NautobotFilterForm):
    model = TaskImplementation
    q = forms.CharField(required=False, label="Search")
    enabled = forms.NullBooleanField(required=False)
    task = DynamicModelMultipleChoiceField(queryset=TaskDefinition.objects.all(), required=False)
    manufacturer = DynamicModelMultipleChoiceField(queryset=Manufacturer.objects.all(), required=False)
    platform = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), required=False)
    tags = TagFilterField(model)


# =============================================================================
# Workflows (Workflow / WorkflowStep)
# =============================================================================


class WorkflowForm(NautobotModelForm):
    class Meta:
        model = Workflow
        fields = [
            "name",
            "slug",
            "description",
            "category",
            "version",
            "enabled",
            "approval_required",
            "schedule_allowed",
            "input_schema",
            "default_inputs",
            "tags",
        ]


class WorkflowBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Workflow.objects.all(), widget=forms.MultipleHiddenInput())
    enabled = forms.NullBooleanField(required=False)
    approval_required = forms.NullBooleanField(required=False)
    schedule_allowed = forms.NullBooleanField(required=False)

    class Meta:
        model = Workflow
        nullable_fields = ["description", "category", "version"]


class WorkflowFilterForm(NautobotFilterForm):
    model = Workflow
    q = forms.CharField(required=False, label="Search")
    enabled = forms.NullBooleanField(required=False)
    tags = TagFilterField(model)


class WorkflowStepForm(NautobotModelForm):
    workflow = DynamicModelChoiceField(queryset=Workflow.objects.all())
    task = DynamicModelChoiceField(queryset=TaskDefinition.objects.all(), required=False)

    class Meta:
        model = WorkflowStep
        fields = [
            "workflow",
            "order",
            "name",
            "step_type",
            "task",
            "input_mapping",
            "output_mapping",
            "condition",
            "on_failure",
            "config",
            "tags",
        ]
        widgets = {
            "input_mapping": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "output_mapping": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "config": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
        }


class WorkflowStepBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=WorkflowStep.objects.all(), widget=forms.MultipleHiddenInput())
    step_type = forms.ChoiceField(choices=WorkflowStep.StepTypeChoices.choices, required=False)
    on_failure = forms.ChoiceField(choices=WorkflowStep.OnFailureChoices.choices, required=False)

    class Meta:
        model = WorkflowStep
        nullable_fields = ["task", "condition"]


class WorkflowStepFilterForm(NautobotFilterForm):
    model = WorkflowStep
    q = forms.CharField(required=False, label="Search")
    workflow = DynamicModelMultipleChoiceField(queryset=Workflow.objects.all(), required=False)
    step_type = forms.MultipleChoiceField(choices=WorkflowStep.StepTypeChoices.choices, required=False)
    tags = TagFilterField(model)


# =============================================================================
# Executions (Execution)
# =============================================================================


class ExecutionBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Execution.objects.all(), widget=forms.MultipleHiddenInput())
    status = forms.ChoiceField(choices=Execution.StatusChoices.choices, required=False)

    class Meta:
        model = Execution
        nullable_fields = ["approved_by", "scheduled_for", "started_at", "completed_at"]


class ExecutionFilterForm(NautobotFilterForm):
    model = Execution
    q = forms.CharField(required=False, label="Search")
    status = forms.MultipleChoiceField(choices=Execution.StatusChoices.choices, required=False)
    workflow = DynamicModelMultipleChoiceField(queryset=Workflow.objects.all(), required=False)
    tags = TagFilterField(model)


# =============================================================================
# Providers (Provider / ProviderConfig)
# =============================================================================


class ProviderForm(NautobotModelForm):
    capabilities = forms.JSONField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 6}))

    class Meta:
        model = Provider
        fields = ["name", "driver_class", "description", "capabilities", "supported_platforms", "enabled", "tags"]


class ProviderBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Provider.objects.all(), widget=forms.MultipleHiddenInput())
    enabled = forms.NullBooleanField(required=False)

    class Meta:
        model = Provider
        nullable_fields = ["description"]


class ProviderFilterForm(NautobotFilterForm):
    model = Provider
    q = forms.CharField(required=False, label="Search")
    enabled = forms.NullBooleanField(required=False)
    tags = TagFilterField(model)


class ProviderConfigForm(NautobotModelForm):
    provider = DynamicModelChoiceField(queryset=Provider.objects.all())
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), required=False, label="Secrets Group")
    settings = forms.JSONField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 8}))

    scope_locations = DynamicModelMultipleChoiceField(queryset=Location.objects.all(), required=False, label="Locations")
    scope_tenants = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False, label="Tenants")
    scope_tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False, label="Tags")
    # Explicit tags field to avoid ModelForm metaclass trying to build a formfield from TaggableManager too early in startup.
    tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False, label="Tags")

    class Meta:
        model = ProviderConfig
        fields = [
            "provider",
            "name",
            "enabled",
            "scope_locations",
            "scope_tenants",
            "scope_tags",
            "secrets_group",
            "settings",
            "tags",
        ]


class ProviderConfigBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ProviderConfig.objects.all(), widget=forms.MultipleHiddenInput())
    enabled = forms.NullBooleanField(required=False)

    class Meta:
        model = ProviderConfig
        nullable_fields = ["secrets_group"]


class ProviderConfigFilterForm(NautobotFilterForm):
    model = ProviderConfig
    q = forms.CharField(required=False, label="Search")
    enabled = forms.NullBooleanField(required=False)
    provider = DynamicModelMultipleChoiceField(queryset=Provider.objects.all(), required=False)
    tags = TagFilterField(model)


# =============================================================================
# Phase 3: Request Forms + Fields (builder CRUD)
# =============================================================================


class RequestFormForm(NautobotModelForm):
    workflow = DynamicModelChoiceField(queryset=Workflow.objects.all())

    class Meta:
        model = RequestForm
        fields = ["name", "slug", "description", "category", "icon", "workflow", "published", "tags"]


class RequestFormBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RequestForm.objects.all(), widget=forms.MultipleHiddenInput())
    published = forms.NullBooleanField(required=False)
    category = forms.CharField(required=False)

    class Meta:
        model = RequestForm
        nullable_fields = ["description", "category", "icon"]


class RequestFormFilterForm(NautobotFilterForm):
    model = RequestForm
    q = forms.CharField(required=False, label="Search")
    published = forms.NullBooleanField(required=False)
    workflow = DynamicModelMultipleChoiceField(queryset=Workflow.objects.all(), required=False)
    tags = TagFilterField(model)


class RequestFormFieldForm(NautobotModelForm):
    form = DynamicModelChoiceField(queryset=RequestForm.objects.all())
    object_type = DynamicModelChoiceField(queryset=ContentType.objects.all().order_by("app_label", "model"), required=False, label="Object Type")
    depends_on = DynamicModelChoiceField(queryset=RequestFormField.objects.all(), required=False, label="Depends On")

    lookup_type = forms.ChoiceField(
        choices=RequestFormField.LookupTypeChoices.choices,
        required=False,
        initial=RequestFormField.LookupTypeChoices.MANUAL,
        widget=forms.Select(attrs={'class': 'form-control', 'onchange': 'toggleLookupFields(this.value)'})
    )

    class Meta:
        model = RequestFormField
        fields = [
            "form",
            "order",
            "field_name",
            "field_type",
            "lookup_type",
            "lookup_config",
            "label",
            "help_text",
            "required",
            "default_value",
            "validation_rules",
            "choices",
            "object_type",
            "queryset_filter",
            "depends_on",
            "show_condition",
            "map_to",
            "tags",
        ]
        widgets = {
            "queryset_filter": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "lookup_config": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "default_value": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "validation_rules": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "choices": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        from django.utils.safestring import mark_safe
        super().__init__(*args, **kwargs)
        self.fields['lookup_type'].help_text = mark_safe("""
            <b>Manual</b>: Use raw JSON in 'Queryset Filter'.<br>
            <b>Location by Type</b>: Set {'type': 'Building'} in config.<br>
            <b>VLAN by Tag</b>: Set {'tag_field': 'service_type'} in config.<br>
            <b>Task by Category</b>: Set {'category': 'Service Catalog'} in config.
        """)
        
        # Add JavaScript to handle UI logic
        if hasattr(self, "helper"):
            self.helper.form_tag = False
        
    class Media:
        js = ('nautobot_network_provisioning/js/form-builder.js',)


class RequestFormFieldBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RequestFormField.objects.all(), widget=forms.MultipleHiddenInput())
    required = forms.NullBooleanField(required=False)
    field_type = forms.ChoiceField(choices=RequestFormField.FieldTypeChoices.choices, required=False)

    class Meta:
        model = RequestFormField
        nullable_fields = ["help_text", "object_type", "depends_on", "show_condition", "map_to"]


class RequestFormFieldFilterForm(NautobotFilterForm):
    model = RequestFormField
    q = forms.CharField(required=False, label="Search")
    form = DynamicModelMultipleChoiceField(queryset=RequestForm.objects.all(), required=False)
    field_type = forms.MultipleChoiceField(choices=RequestFormField.FieldTypeChoices.choices, required=False)
    tags = TagFilterField(model)


