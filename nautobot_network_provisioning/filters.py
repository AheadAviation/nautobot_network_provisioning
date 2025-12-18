"""FilterSets for the Network Provisioning (Automation) app."""

from __future__ import annotations

import django_filters
from nautobot.apps.filters import NautobotFilterSet, SearchFilter
from nautobot.dcim.models import Manufacturer, Platform

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


class TaskDefinitionFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "slug": "icontains", "description": "icontains"})
    category = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = TaskDefinition
        fields = ["id", "slug", "category"]


class TaskImplementationFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "task__name": "icontains", "template_content": "icontains"})
    enabled = django_filters.BooleanFilter()
    task = django_filters.ModelMultipleChoiceFilter(queryset=TaskDefinition.objects.all())
    manufacturer = django_filters.ModelMultipleChoiceFilter(queryset=Manufacturer.objects.all())
    platform = django_filters.ModelMultipleChoiceFilter(queryset=Platform.objects.all())
    software_versions = django_filters.ModelMultipleChoiceFilter(
        field_name="software_versions",
        queryset=None,
    )
    implementation_type = django_filters.MultipleChoiceFilter(choices=TaskImplementation.ImplementationTypeChoices.choices)

    class Meta:
        model = TaskImplementation
        fields = ["id", "enabled", "task", "manufacturer", "platform", "software_versions", "implementation_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from nautobot.dcim.models import SoftwareVersion

        self.filters["software_versions"].queryset = SoftwareVersion.objects.all()


class WorkflowFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "slug": "icontains", "description": "icontains"})
    enabled = django_filters.BooleanFilter()

    class Meta:
        model = Workflow
        fields = ["id", "slug", "enabled"]


class WorkflowStepFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"workflow__name": "icontains", "name": "icontains"})
    workflow = django_filters.ModelMultipleChoiceFilter(queryset=Workflow.objects.all())
    step_type = django_filters.MultipleChoiceFilter(choices=WorkflowStep.StepTypeChoices.choices)

    class Meta:
        model = WorkflowStep
        fields = ["id", "workflow", "step_type", "order"]


class ExecutionFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"workflow__name": "icontains"})
    status = django_filters.MultipleChoiceFilter(choices=Execution.StatusChoices.choices)
    workflow = django_filters.ModelMultipleChoiceFilter(queryset=Workflow.objects.all())

    class Meta:
        model = Execution
        fields = ["id", "status", "workflow", "requested_by", "approved_by", "scheduled_for"]


class ProviderFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "driver_class": "icontains", "description": "icontains"})
    enabled = django_filters.BooleanFilter()

    class Meta:
        model = Provider
        fields = ["id", "name", "enabled"]


class ProviderConfigFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "provider__name": "icontains"})
    enabled = django_filters.BooleanFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=Provider.objects.all())

    class Meta:
        model = ProviderConfig
        fields = ["id", "provider", "name", "enabled"]


class RequestFormFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "slug": "icontains", "description": "icontains"})
    published = django_filters.BooleanFilter()
    workflow = django_filters.ModelMultipleChoiceFilter(queryset=Workflow.objects.all())

    class Meta:
        model = RequestForm
        fields = ["id", "slug", "published", "workflow", "category"]


class RequestFormFieldFilterSet(NautobotFilterSet):
    q = SearchFilter(filter_predicates={"form__name": "icontains", "field_name": "icontains", "label": "icontains"})
    form = django_filters.ModelMultipleChoiceFilter(queryset=RequestForm.objects.all())
    field_type = django_filters.MultipleChoiceFilter(choices=RequestFormField.FieldTypeChoices.choices)

    class Meta:
        model = RequestFormField
        fields = ["id", "form", "field_type", "order", "field_name"]


