"""UI Views for the Network Provisioning (Automation) app."""

from __future__ import annotations

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


class WorkflowUIViewSet(NautobotUIViewSet):
    queryset = Workflow.objects.all()
    table_class = WorkflowTable
    form_class = WorkflowForm
    filterset_class = WorkflowFilterSet
    filterset_form_class = WorkflowFilterForm
    bulk_update_form_class = WorkflowBulkEditForm
    serializer_class = WorkflowSerializer
    lookup_field = "pk"


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


class RequestFormFieldUIViewSet(NautobotUIViewSet):
    queryset = RequestFormField.objects.select_related("form", "object_type", "depends_on")
    table_class = RequestFormFieldTable
    form_class = RequestFormFieldForm
    filterset_class = RequestFormFieldFilterSet
    filterset_form_class = RequestFormFieldFilterForm
    bulk_update_form_class = RequestFormFieldBulkEditForm
    serializer_class = RequestFormFieldSerializer
    lookup_field = "pk"
