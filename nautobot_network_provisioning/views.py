"""UI Views for the Network Provisioning (Automation) app."""

from __future__ import annotations

import json
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from nautobot.apps.views import NautobotUIViewSet

from nautobot_network_provisioning.api.serializers import (
    ExecutionSerializer,
    ProviderConfigSerializer,
    ProviderSerializer,
    RequestFormFieldSerializer,
    RequestFormSerializer,
    TaskDefinitionSerializer,
    TaskImplementationSerializer,
    WorkflowSerializer,
    WorkflowStepSerializer,
)
from nautobot_network_provisioning.filters import (
    ExecutionFilterSet,
    ProviderConfigFilterSet,
    ProviderFilterSet,
    RequestFormFieldFilterSet,
    RequestFormFilterSet,
    TaskDefinitionFilterSet,
    TaskImplementationFilterSet,
    WorkflowFilterSet,
    WorkflowStepFilterSet,
)
from nautobot_network_provisioning.forms import (
    ExecutionBulkEditForm,
    ExecutionFilterForm,
    ProviderBulkEditForm,
    ProviderConfigBulkEditForm,
    ProviderConfigFilterForm,
    ProviderConfigForm,
    ProviderFilterForm,
    ProviderForm,
    RequestFormBulkEditForm,
    RequestFormFieldBulkEditForm,
    RequestFormFieldFilterForm,
    RequestFormFieldForm,
    RequestFormFilterForm,
    RequestFormForm,
    TaskDefinitionBulkEditForm,
    TaskDefinitionFilterForm,
    TaskDefinitionForm,
    TaskImplementationBulkEditForm,
    TaskImplementationFilterForm,
    TaskImplementationForm,
    WorkflowBulkEditForm,
    WorkflowFilterForm,
    WorkflowForm,
    WorkflowStepBulkEditForm,
    WorkflowStepFilterForm,
    WorkflowStepForm,
)
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
from nautobot_network_provisioning.tables import (
    ExecutionTable,
    ProviderConfigTable,
    ProviderTable,
    RequestFormFieldTable,
    RequestFormTable,
    TaskDefinitionTable,
    TaskImplementationTable,
    WorkflowStepTable,
    WorkflowTable,
)


class TaskDefinitionUIViewSet(NautobotUIViewSet):
    queryset = TaskDefinition.objects.all()
    table_class = TaskDefinitionTable
    form_class = TaskDefinitionForm
    filterset_class = TaskDefinitionFilterSet
    filterset_form_class = TaskDefinitionFilterForm
    bulk_update_form_class = TaskDefinitionBulkEditForm
    serializer_class = TaskDefinitionSerializer
    lookup_field = "pk"


class TaskImplementationUIViewSet(NautobotUIViewSet):
    queryset = TaskImplementation.objects.select_related("task", "manufacturer", "platform", "provider_config")
    table_class = TaskImplementationTable
    form_class = TaskImplementationForm
    filterset_class = TaskImplementationFilterSet
    filterset_form_class = TaskImplementationFilterForm
    bulk_update_form_class = TaskImplementationBulkEditForm
    serializer_class = TaskImplementationSerializer
    lookup_field = "pk"

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action in ["retrieve", "edit"] and instance:
            context["object"] = instance
        return context

    def dispatch(self, request, *args, **kwargs):
        """Redirect to IDE for template-based implementations on edit/retrieve if desired."""
        if kwargs.get("pk") and request.method == "GET" and ("edit" in request.path or request.GET.get("edit")):
            try:
                instance = self.queryset.filter(pk=kwargs.get("pk")).first()
                if instance and instance.implementation_type in ["jinja2_config", "jinja2_payload", "graphql_query"]:
                    return redirect(reverse("plugins:nautobot_network_provisioning:template_ide", kwargs={"pk": instance.pk}))
            except Exception:
                pass
        return super().dispatch(request, *args, **kwargs)


class WorkflowUIViewSet(NautobotUIViewSet):
    queryset = Workflow.objects.all()
    table_class = WorkflowTable
    form_class = WorkflowForm
    filterset_class = WorkflowFilterSet
    filterset_form_class = WorkflowFilterForm
    bulk_update_form_class = WorkflowBulkEditForm
    serializer_class = WorkflowSerializer
    lookup_field = "pk"

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve" and instance:
            context["steps"] = instance.steps.all().order_by("order")
        return context


class WorkflowStepUIViewSet(NautobotUIViewSet):
    queryset = WorkflowStep.objects.select_related("workflow", "task")
    table_class = WorkflowStepTable
    form_class = WorkflowStepForm
    filterset_class = WorkflowStepFilterSet
    filterset_form_class = WorkflowStepFilterForm
    bulk_update_form_class = WorkflowStepBulkEditForm
    serializer_class = WorkflowStepSerializer
    lookup_field = "pk"


class ExecutionUIViewSet(NautobotUIViewSet):
    queryset = Execution.objects.select_related("workflow", "requested_by", "approved_by").prefetch_related("target_devices")
    table_class = ExecutionTable
    filterset_class = ExecutionFilterSet
    filterset_form_class = ExecutionFilterForm
    bulk_update_form_class = ExecutionBulkEditForm
    serializer_class = ExecutionSerializer
    lookup_field = "pk"
    action_buttons = ("export",)

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve" and instance:
            context["steps"] = instance.steps.all().order_by("order")
        return context


class ProviderUIViewSet(NautobotUIViewSet):
    queryset = Provider.objects.all()
    table_class = ProviderTable
    form_class = ProviderForm
    filterset_class = ProviderFilterSet
    filterset_form_class = ProviderFilterForm
    bulk_update_form_class = ProviderBulkEditForm
    serializer_class = ProviderSerializer
    lookup_field = "pk"


class ProviderConfigUIViewSet(NautobotUIViewSet):
    queryset = ProviderConfig.objects.select_related("provider", "secrets_group").prefetch_related(
        "scope_locations", "scope_tenants", "scope_tags"
    )
    table_class = ProviderConfigTable
    form_class = ProviderConfigForm
    filterset_class = ProviderConfigFilterSet
    filterset_form_class = ProviderConfigFilterForm
    bulk_update_form_class = ProviderConfigBulkEditForm
    serializer_class = ProviderConfigSerializer
    lookup_field = "pk"


class RequestFormUIViewSet(NautobotUIViewSet):
    queryset = RequestForm.objects.select_related("workflow")
    table_class = RequestFormTable
    form_class = RequestFormForm
    filterset_class = RequestFormFilterSet
    filterset_form_class = RequestFormFilterForm
    bulk_update_form_class = RequestFormBulkEditForm
    serializer_class = RequestFormSerializer
    lookup_field = "pk"

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve" and instance:
            context["fields"] = instance.fields.all().order_by("order")
        return context


class RequestFormFieldUIViewSet(NautobotUIViewSet):
    queryset = RequestFormField.objects.select_related("form", "object_type", "depends_on")
    table_class = RequestFormFieldTable
    form_class = RequestFormFieldForm
    filterset_class = RequestFormFieldFilterSet
    filterset_form_class = RequestFormFieldFilterForm
    bulk_update_form_class = RequestFormFieldBulkEditForm
    serializer_class = RequestFormFieldSerializer
    lookup_field = "pk"


class TemplateIDEView(LoginRequiredMixin, View):
    """
    GraphiQL-style IDE for developing and testing Jinja2 templates.
    """
    template_name = "nautobot_network_provisioning/template_ide.html"

    def get(self, request, pk=None):
        """Render the IDE, optionally pre-loading a TaskImplementation."""
        context = {
            "template_content": "",
            "variables_json": json.dumps({"device": {"name": "example-device"}, "inputs": {}}, indent=2),
            "implementation": None,
        }

        if pk:
            implementation = get_object_or_404(TaskImplementation, pk=pk)
            context["implementation"] = implementation
            context["template_content"] = implementation.template_content
            
            # Try to build a sample variables JSON from the task's input schema
            if implementation.task and implementation.task.input_schema:
                sample_inputs = {}
                properties = implementation.task.input_schema.get("properties", {})
                for key, prop in properties.items():
                    prop_type = prop.get("type")
                    if prop_type == "integer":
                        sample_inputs[key] = 1
                    elif prop_type == "boolean":
                        sample_inputs[key] = True
                    elif prop_type == "object":
                        sample_inputs[key] = {}
                    elif prop_type == "array":
                        sample_inputs[key] = []
                    else:
                        sample_inputs[key] = "sample_value"
                
                context["variables_json"] = json.dumps({
                    "device": {
                        "name": "demo-switch-01",
                        "platform": str(implementation.platform) if implementation.platform else "ios",
                    },
                    "intended": {
                        "inputs": sample_inputs
                    }
                }, indent=2)

        return render(request, self.template_name, context)


class AutomationHomeView(LoginRequiredMixin, View):
    """
    Overview dashboard for the Automation App.
    """
    template_name = "nautobot_network_provisioning/home.html"

    def get(self, request):
        context = {
            "task_count": TaskDefinition.objects.count(),
            "tasks": TaskDefinition.objects.all().order_by("category", "name"),
            "workflow_count": Workflow.objects.count(),
            "execution_count": Execution.objects.count(),
            "recent_executions": Execution.objects.order_by("-created")[:5],
            "active_workflows": Workflow.objects.filter(enabled=True)[:5],
            "published_forms": RequestForm.objects.filter(published=True).count(),
        }
        return render(request, self.template_name, context)


class RequestFormBuilderView(LoginRequiredMixin, View):
    """
    Experimental Form Builder view.
    """
    template_name = "nautobot_network_provisioning/requestform_builder.html"

    def get(self, request, pk):
        rf = get_object_or_404(RequestForm, pk=pk)
        fields = rf.fields.all().order_by("order")
        return render(request, self.template_name, {"object": rf, "fields": fields})


class WorkflowDesignerView(LoginRequiredMixin, View):
    """
    Experimental Workflow Designer view.
    """
    template_name = "nautobot_network_provisioning/workflow_designer.html"

    def get(self, request, pk):
        workflow = get_object_or_404(Workflow, pk=pk)
        steps = workflow.steps.all().order_by("order")
        return render(request, self.template_name, {"object": workflow, "steps": steps})
