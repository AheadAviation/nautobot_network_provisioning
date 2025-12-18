"""REST API Serializers for the Network Provisioning (Automation) app."""

from __future__ import annotations

from nautobot.apps.api import NautobotModelSerializer

from nautobot_network_provisioning.models import (
    Execution,
    ExecutionStep,
    Provider,
    ProviderConfig,
    RequestForm,
    RequestFormField,
    TaskDefinition,
    TaskImplementation,
    Workflow,
    WorkflowStep,
)


class TaskDefinitionSerializer(NautobotModelSerializer):
    class Meta:
        model = TaskDefinition
        fields = "__all__"


class TaskImplementationSerializer(NautobotModelSerializer):
    class Meta:
        model = TaskImplementation
        fields = "__all__"


class WorkflowSerializer(NautobotModelSerializer):
    class Meta:
        model = Workflow
        fields = "__all__"


class WorkflowStepSerializer(NautobotModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = "__all__"


class ExecutionSerializer(NautobotModelSerializer):
    class Meta:
        model = Execution
        fields = "__all__"


class ExecutionStepSerializer(NautobotModelSerializer):
    class Meta:
        model = ExecutionStep
        fields = "__all__"


class ProviderSerializer(NautobotModelSerializer):
    class Meta:
        model = Provider
        fields = "__all__"


class ProviderConfigSerializer(NautobotModelSerializer):
    class Meta:
        model = ProviderConfig
        fields = "__all__"


class RequestFormSerializer(NautobotModelSerializer):
    class Meta:
        model = RequestForm
        fields = "__all__"


class RequestFormFieldSerializer(NautobotModelSerializer):
    class Meta:
        model = RequestFormField
        fields = "__all__"


