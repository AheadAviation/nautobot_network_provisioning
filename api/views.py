"""REST API Views for the NetAccess app."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from nautobot.apps.api import NautobotModelViewSet

from nautobot_network_provisioning.models import (
    PortService,
    SwitchProfile,
    ConfigTemplate,
    ConfigTemplateHistory,
    JackMapping,
    WorkQueueEntry,
    MACAddress,
    MACAddressEntry,
    MACAddressHistory,
    ARPEntry,
    ControlSetting,
)
from nautobot_network_provisioning.filters import (
    PortServiceFilterSet,
    SwitchProfileFilterSet,
    ConfigTemplateFilterSet,
    JackMappingFilterSet,
    WorkQueueEntryFilterSet,
    MACAddressFilterSet,
    MACAddressEntryFilterSet,
    MACAddressHistoryFilterSet,
    ARPEntryFilterSet,
    ControlSettingFilterSet,
)
from nautobot_network_provisioning.api.serializers import (
    PortServiceSerializer,
    SwitchProfileSerializer,
    ConfigTemplateSerializer,
    JackMappingSerializer,
    WorkQueueEntrySerializer,
    MACAddressSerializer,
    MACAddressEntrySerializer,
    MACAddressHistorySerializer,
    ARPEntrySerializer,
    ControlSettingSerializer,
)
from nautobot_network_provisioning.validators import validate_jinja2_syntax
from nautobot_network_provisioning.services.template_renderer import render_template_from_context


class PortServiceViewSet(NautobotModelViewSet):
    """API ViewSet for PortService model."""

    queryset = PortService.objects.all()
    serializer_class = PortServiceSerializer
    filterset_class = PortServiceFilterSet


class SwitchProfileViewSet(NautobotModelViewSet):
    """API ViewSet for SwitchProfile model."""

    queryset = SwitchProfile.objects.all()
    serializer_class = SwitchProfileSerializer
    filterset_class = SwitchProfileFilterSet


class ConfigTemplateViewSet(NautobotModelViewSet):
    """API ViewSet for ConfigTemplate model."""

    queryset = ConfigTemplate.objects.all()
    serializer_class = ConfigTemplateSerializer
    filterset_class = ConfigTemplateFilterSet


class JackMappingViewSet(NautobotModelViewSet):
    """API ViewSet for JackMapping model."""

    queryset = JackMapping.objects.all()
    serializer_class = JackMappingSerializer
    filterset_class = JackMappingFilterSet


class WorkQueueEntryViewSet(NautobotModelViewSet):
    """API ViewSet for WorkQueueEntry model."""

    queryset = WorkQueueEntry.objects.all()
    serializer_class = WorkQueueEntrySerializer
    filterset_class = WorkQueueEntryFilterSet


class MACAddressViewSet(NautobotModelViewSet):
    """API ViewSet for MACAddress model."""

    queryset = MACAddress.objects.all()
    serializer_class = MACAddressSerializer
    filterset_class = MACAddressFilterSet


class MACAddressEntryViewSet(NautobotModelViewSet):
    """API ViewSet for MACAddressEntry model."""

    queryset = MACAddressEntry.objects.all()
    serializer_class = MACAddressEntrySerializer
    filterset_class = MACAddressEntryFilterSet


class MACAddressHistoryViewSet(NautobotModelViewSet):
    """API ViewSet for MACAddressHistory model."""

    queryset = MACAddressHistory.objects.all()
    serializer_class = MACAddressHistorySerializer
    filterset_class = MACAddressHistoryFilterSet


class ARPEntryViewSet(NautobotModelViewSet):
    """API ViewSet for ARPEntry model."""

    queryset = ARPEntry.objects.all()
    serializer_class = ARPEntrySerializer
    filterset_class = ARPEntryFilterSet


class ControlSettingViewSet(NautobotModelViewSet):
    """API ViewSet for ControlSetting model."""

    queryset = ControlSetting.objects.all()
    serializer_class = ControlSettingSerializer
    filterset_class = ControlSettingFilterSet


# =============================================================================
# Template Preview and Validation API
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def template_preview(request):
    """
    Preview and/or validate a Jinja2 template.
    
    POST body:
    {
        "template_text": "interface {{ interface }}...",
        "context": {  // Optional custom context
            "interface": "GigabitEthernet1/0/5",
            ...
        },
        "validate_only": false  // If true, only validate without rendering
    }
    
    Response:
    {
        "is_valid": true/false,
        "errors": [],
        "warnings": [],
        "rendered": "interface GigabitEthernet1/0/1...",  // Only if is_valid and not validate_only
        "template_type": "pure_jinja2"
    }
    """
    template_text = request.data.get('template_text', '')
    custom_context = request.data.get('context', {})
    validate_only = request.data.get('validate_only', False)
    
    if not template_text:
        return Response({
            'is_valid': False,
            'errors': ['No template text provided'],
            'warnings': [],
            'rendered': None,
            'template_type': None,
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate the template
    validation_result = validate_jinja2_syntax(template_text)
    
    response_data = {
        'is_valid': validation_result.is_valid,
        'errors': [str(e) for e in validation_result.errors],
        'warnings': validation_result.warnings,
        'template_type': validation_result.template_type,
    }
    
    # If validation only or invalid, return now
    if validate_only or not validation_result.is_valid:
        response_data['rendered'] = None
        return Response(response_data)
    
    # Build preview context
    preview_context = {
        "interface": "GigabitEthernet1/0/1",
        "interface_name": "GigabitEthernet1/0/1",
        "interface_short": "Gi1/0/1",
        "device": None,
        "device_name": "demo-switch-01",
        "device_ip": "10.10.10.1",
        "building": None,
        "building_name": "Main Building",
        "comm_room": "MDF-1",
        "jack": "A-101",
        "vlan": 100,
        "vlan_name": "Data-VLAN",
        "voice_vlan": 200,
        "service": None,
        "service_name": "Access-Data",
        "requested_by": "jsmith",
        "creator": "admin",
        "template_version": 1,
        "template_instance": 1,
    }
    
    # Merge with custom context
    preview_context.update(custom_context)
    
    # Render the template
    try:
        rendered = render_template_from_context(template_text, preview_context)
        response_data['rendered'] = rendered
    except Exception as e:
        response_data['is_valid'] = False
        response_data['errors'].append(f"Render error: {str(e)}")
        response_data['rendered'] = None
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def template_validate(request):
    """
    Validate a Jinja2 template without rendering.
    
    POST body:
    {
        "template_text": "interface {{ interface }}..."
    }
    
    Response:
    {
        "is_valid": true/false,
        "errors": [],
        "warnings": [],
        "template_type": "pure_jinja2"
    }
    """
    template_text = request.data.get('template_text', '')
    
    if not template_text:
        return Response({
            'is_valid': False,
            'errors': ['No template text provided'],
            'warnings': [],
            'template_type': None,
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate the template
    validation_result = validate_jinja2_syntax(template_text)
    
    return Response({
        'is_valid': validation_result.is_valid,
        'errors': [str(e) for e in validation_result.errors],
        'warnings': validation_result.warnings,
        'template_type': validation_result.template_type,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_variables(request):
    """
    Return available template variables for the helper panel.
    
    Response:
    {
        "categories": [
            {
                "name": "Interface",
                "variables": [
                    {"name": "interface", "example": "GigabitEthernet1/0/1", "description": "..."}
                ]
            }
        ],
        "filters": [...],
        "control_structures": [...]
    }
    """
    from nautobot_network_provisioning.widgets import Jinja2EditorWidget
    
    return Response({
        'categories': Jinja2EditorWidget.TEMPLATE_VARIABLES,
        'filters': Jinja2EditorWidget.JINJA2_FILTERS,
        'control_structures': Jinja2EditorWidget.JINJA2_STRUCTURES,
    })
