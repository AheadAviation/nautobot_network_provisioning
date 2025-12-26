from django import forms
from nautobot.apps.forms import NautobotModelForm
from .models import TaskIntent, Workflow, RequestForm, Execution, AutomationProvider, AutomationProviderConfig, TaskStrategy


class TaskIntentForm(NautobotModelForm):
    class Meta:
        model = TaskIntent
        fields = (
            "name",
            "slug",
            "input_schema",
            "variable_mappings",
            "description",
        )

class TaskStrategyForm(NautobotModelForm):
    class Meta:
        model = TaskStrategy
        fields = (
            "task_intent",
            "platform",
            "logic_type",
            "template_content",
            "enabled",
            "priority",
        )


class WorkflowForm(NautobotModelForm):
    class Meta:
        model = Workflow
        fields = ("name", "slug", "description", "graph_definition", "enabled", "approval_required")


class RequestFormForm(NautobotModelForm):
    class Meta:
        model = RequestForm
        fields = ("name", "slug", "workflow", "description", "published", "field_definition")


class ExecutionForm(NautobotModelForm):
    class Meta:
        model = Execution
        fields = ("workflow", "request_form", "status", "input_data")


class AutomationProviderForm(NautobotModelForm):
    class Meta:
        model = AutomationProvider
        fields = ("name", "slug", "driver_class", "supported_platforms", "description", "enabled")


class AutomationProviderConfigForm(NautobotModelForm):
    class Meta:
        model = AutomationProviderConfig
        fields = (
            "name",
            "slug",
            "provider",
            "parameters",
            "secrets_group",
            "scope_locations",
            "scope_tenants",
            "enabled",
            "description",
        )
