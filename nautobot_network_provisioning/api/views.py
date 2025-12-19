"""REST API Views for the Network Provisioning (Automation) app."""

from __future__ import annotations

from nautobot.apps.api import NautobotModelViewSet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from nautobot_network_provisioning.api.serializers import (
    ExecutionSerializer,
    ExecutionStepSerializer,
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
from nautobot_network_provisioning.services.template_renderer import build_context, render_template_from_context


def _serialize_context(context):
    """Recursively serialize context for JSON response."""
    if isinstance(context, dict):
        return {k: _serialize_context(v) for k, v in context.items()}
    if isinstance(context, (list, tuple)):
        return [_serialize_context(v) for v in context]
    if hasattr(context, "pk"):
        return str(context.pk)
    if hasattr(context, "all"):
        # Handle QuerySets
        return [_serialize_context(obj) for obj in context.all()]
    # Basic types are fine
    if isinstance(context, (str, int, float, bool, type(None))):
        return context
    # Fallback for complex objects: use str() or similar
    return str(context)


class TaskDefinitionViewSet(NautobotModelViewSet):
    queryset = TaskDefinition.objects.all()
    serializer_class = TaskDefinitionSerializer
    filterset_class = TaskDefinitionFilterSet


class TaskImplementationViewSet(NautobotModelViewSet):
    queryset = TaskImplementation.objects.all()
    serializer_class = TaskImplementationSerializer
    filterset_class = TaskImplementationFilterSet


class WorkflowViewSet(NautobotModelViewSet):
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    filterset_class = WorkflowFilterSet


class WorkflowStepViewSet(NautobotModelViewSet):
    queryset = WorkflowStep.objects.all()
    serializer_class = WorkflowStepSerializer
    filterset_class = WorkflowStepFilterSet


class ExecutionViewSet(NautobotModelViewSet):
    queryset = Execution.objects.all()
    serializer_class = ExecutionSerializer
    filterset_class = ExecutionFilterSet


class ExecutionStepViewSet(NautobotModelViewSet):
    queryset = ExecutionStep.objects.all()
    serializer_class = ExecutionStepSerializer


class ProviderViewSet(NautobotModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    filterset_class = ProviderFilterSet


class ProviderConfigViewSet(NautobotModelViewSet):
    queryset = ProviderConfig.objects.all()
    serializer_class = ProviderConfigSerializer
    filterset_class = ProviderConfigFilterSet


class RequestFormViewSet(NautobotModelViewSet):
    queryset = RequestForm.objects.all()
    serializer_class = RequestFormSerializer
    filterset_class = RequestFormFilterSet


class RequestFormFieldViewSet(NautobotModelViewSet):
    queryset = RequestFormField.objects.all()
    serializer_class = RequestFormFieldSerializer
    filterset_class = RequestFormFieldFilterSet


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def template_preview(request):
    """
    Preview a Jinja2 template using a supplied context.

    Request body:
    - template_text: string (or "template")
    - context: object (dict)
    - validate_only: bool
    """
    template_text = request.data.get("template_text") or request.data.get("template") or ""
    context = request.data.get("context") or {}
    validate_only = bool(request.data.get("validate_only", False))

    if not template_text:
        return Response(
            {"is_valid": False, "errors": ["No template text provided"], "warnings": [], "rendered": None, "template_type": None},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(context, dict):
        return Response(
            {"is_valid": False, "errors": ["context must be an object/dict"], "warnings": [], "rendered": None, "template_type": None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from jinja2 import Environment

        # Parse to validate syntax first (no rendering side effects).
        env = Environment()
        env.parse(template_text or "")
    except Exception as e:  # noqa: BLE001
        return Response(
            {"is_valid": False, "errors": [str(e)], "warnings": [], "rendered": None, "template_type": "jinja2"},
            status=status.HTTP_200_OK,
        )

    if validate_only:
        return Response({"is_valid": True, "errors": [], "warnings": [], "rendered": None, "template_type": "jinja2"})

    try:
        rendered = render_template_from_context(template_text, context)
        return Response({"is_valid": True, "errors": [], "warnings": [], "rendered": rendered, "template_type": "jinja2"})
    except Exception as e:  # noqa: BLE001
        return Response(
            {"is_valid": False, "errors": [f"Render error: {e}"], "warnings": [], "rendered": None, "template_type": "jinja2"},
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def device_context(request, pk):
    """
    Get the standard rendering context for a specific device.
    """
    from nautobot.dcim.models import Device
    
    device = get_object_or_404(Device, pk=pk)
    context = build_context(device=device)
    
    # Serialize context for JSON
    serialized_context = _serialize_context(context)
    
    return Response(serialized_context)


