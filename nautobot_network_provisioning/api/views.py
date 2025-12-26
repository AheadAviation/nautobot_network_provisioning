"""
API Views v2.0

Provides REST API endpoints for all provisioning models.
Includes new TaskStrategy endpoints and enhanced preview capabilities.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from nautobot.apps.api import NautobotModelViewSet
from ..models import TaskIntent, TaskStrategy, Workflow, Folder, RequestForm, Execution
from . import serializers
from ..services.validator import TaskValidator
from ..services.template_renderer import render_template_from_context, build_context
from ..services.context_resolver import ContextResolver


# ═══════════════════════════════════════════════════════════════════════════
# MODEL VIEWSETS
# ═══════════════════════════════════════════════════════════════════════════

class TaskIntentViewSet(NautobotModelViewSet):
    """
    API endpoint for TaskIntent CRUD operations.
    
    Supports:
    - GET /api/plugins/nautobot-network-provisioning/task-intents/
    - POST /api/plugins/nautobot-network-provisioning/task-intents/
    - GET /api/plugins/nautobot-network-provisioning/task-intents/{id}/
    - PUT/PATCH /api/plugins/nautobot-network-provisioning/task-intents/{id}/
    - DELETE /api/plugins/nautobot-network-provisioning/task-intents/{id}/
    """
    queryset = TaskIntent.objects.prefetch_related('strategies', 'strategies__platform').all()
    serializer_class = serializers.TaskIntentSerializer
    
    def get_serializer_class(self):
        """Use lightweight serializer for list views."""
        if self.action == 'list':
            return serializers.TaskIntentListSerializer
        return serializers.TaskIntentSerializer
    
    @action(detail=True, methods=['get'])
    def strategies(self, request, pk=None):
        """Get all strategies for a specific task intent."""
        task = self.get_object()
        strategies = task.strategies.all()
        serializer = serializers.TaskStrategySerializer(strategies, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def yaml(self, request, pk=None):
        """Export task as YAML-compatible dictionary."""
        task = self.get_object()
        return Response(task.to_yaml_dict())


class TaskStrategyViewSet(NautobotModelViewSet):
    """
    API endpoint for TaskStrategy CRUD operations.
    
    This is where the actual implementation templates live.
    
    Supports:
    - GET /api/plugins/nautobot-network-provisioning/task-strategies/
    - POST /api/plugins/nautobot-network-provisioning/task-strategies/
    - GET /api/plugins/nautobot-network-provisioning/task-strategies/{id}/
    - PUT/PATCH /api/plugins/nautobot-network-provisioning/task-strategies/{id}/
    - DELETE /api/plugins/nautobot-network-provisioning/task-strategies/{id}/
    """
    queryset = TaskStrategy.objects.select_related('task_intent', 'platform', 'platform__manufacturer').all()
    serializer_class = serializers.TaskStrategySerializer
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Render this strategy's template with provided context.
        
        Request body:
        {
            "device_id": "uuid",
            "context_overrides": {"var": "value"}
        }
        """
        strategy = self.get_object()
        device_id = request.data.get('device_id')
        context_overrides = request.data.get('context_overrides', {})
        
        if not device_id:
            return Response(
                {"error": "device_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from nautobot.dcim.models import Device
        try:
            device = Device.objects.get(pk=device_id)
        except Device.DoesNotExist:
            return Response(
                {"error": f"Device not found: {device_id}"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Resolve context from task inputs
        resolver = ContextResolver(device, overrides=context_overrides)
        variable_mappings = strategy.task_intent.inputs or []
        resolved = resolver.resolve(variable_mappings)
        
        # Build render context
        render_context = build_context(
            device=resolved.get("device", {}),
            intended=resolved.get("intended", {}),
            extra={"config_context": resolver.config_context}
        )
        
        # Render template
        try:
            from jinja2 import Environment, DebugUndefined
            env = Environment(undefined=DebugUndefined, trim_blocks=True, lstrip_blocks=True)
            template = env.from_string(strategy.effective_template)
            rendered = template.render(**render_context)
            
            return Response({
                "success": True,
                "rendered": rendered,
                "context": render_context,
                "strategy": {
                    "id": str(strategy.pk),
                    "name": strategy.name,
                    "method": strategy.method,
                    "platform": strategy.platform.name if strategy.platform else None
                }
            })
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e),
                "context": render_context
            })


class WorkflowViewSet(NautobotModelViewSet):
    queryset = Workflow.objects.all()
    serializer_class = serializers.WorkflowSerializer


class FolderViewSet(NautobotModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = serializers.FolderSerializer


class RequestFormViewSet(NautobotModelViewSet):
    queryset = RequestForm.objects.all()
    serializer_class = serializers.RequestFormSerializer


class ExecutionViewSet(NautobotModelViewSet):
    queryset = Execution.objects.all()
    serializer_class = serializers.ExecutionSerializer


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_task(request):
    """
    Validate a task's template and configuration.
    
    Request body:
    {
        "template_content": "{% for server in ... %}",
        "variables": [{"name": "ntp_servers", "source": "input"}],
        "rendered": "optional rendered output for rule validation",
        "validation_rules": [{"type": "contains", "value": "ntp server"}]
    }
    """
    data = request.data
    validator = TaskValidator()
    results = validator.run_all(data)
    
    # Optional: validate rendered output against rules
    rendered = data.get("rendered")
    rules = data.get("validation_rules")
    if rendered and rules:
        results["rule_results"] = validator.validate_rendered_output(rendered, rules)
    
    # Determine overall success
    success = all(
        r.get("success", True) 
        for r in results.values() 
        if isinstance(r, dict) and "success" in r
    )
    
    return Response({
        "results": results,
        "success": success
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def template_preview(request):
    """
    Simple template preview - renders template with provided context.
    
    Request body:
    {
        "template_content": "{% for server in ntp_servers %}...",
        "context": {"ntp_servers": ["10.0.0.1", "10.0.0.2"]}
    }
    """
    template_text = request.data.get("template_content") or ""
    context = request.data.get("context") or {}
    
    try:
        rendered = render_template_from_context(template_text, context)
        return Response({
            "is_valid": True,
            "rendered": rendered
        })
    except Exception as e:
        return Response({
            "is_valid": False,
            "error": str(e)
        }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def render_preview(request):
    """
    Advanced template preview - resolves context from a real device.
    
    Request body:
    {
        "template_content": "{% for server in ntp_servers %}...",  # or "template_code"
        "device_id": "uuid",
        "context_overrides": {"ntp_servers": ["10.0.0.1"]},  # or "variables"
        "variable_mappings": [{"name": "source_interface", "source": "config_context", "path": "ntp.source"}]
    }
    """
    # Support both parameter names for backwards compatibility
    template_code = request.data.get("template_content") or request.data.get("template_code", "")
    device_id = request.data.get("device_id")
    context_overrides = request.data.get("variables") or request.data.get("context_overrides", {})
    variable_mappings = request.data.get("variable_mappings", [])
    
    if not device_id:
        return Response(
            {"error": "device_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from nautobot.dcim.models import Device
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return Response(
            {"error": f"Device not found: {device_id}"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    resolver = ContextResolver(device, overrides=context_overrides)
    resolved = resolver.resolve(variable_mappings)
    
    render_context = build_context(
        device=resolved.get("device", {}),
        intended=resolved.get("intended", {}),
        extra={"config_context": resolver.config_context}
    )
    
    try:
        from jinja2 import Environment, DebugUndefined
        env = Environment(undefined=DebugUndefined, trim_blocks=True, lstrip_blocks=True)
        template = env.from_string(template_code)
        rendered = template.render(**render_context)
        
        return Response({
            "rendered_content": rendered,  # Match frontend expectation
            "rendered_result": rendered,   # Keep for backwards compatibility
            "context": render_context,     # Match frontend expectation
            "resolved_context": resolved,  # Keep for backwards compatibility
            "success": True
        })
    except Exception as e:
        return Response({
            "rendered_content": None,
            "rendered_result": str(e),
            "context": render_context,
            "resolved_context": resolved,
            "success": False,
            "error": str(e)
        })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def model_metadata(request):
    """
    Get metadata about a Nautobot model for building variable references.
    
    Query params:
    - model: Model path (e.g., "dcim.device")
    """
    model_path = request.query_params.get("model")
    if not model_path or "." not in model_path:
        return Response(
            {"error": "Query parameter 'model' required in format 'app.model'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    app_label, model_name = model_path.split(".", 1)
    
    from django.contrib.contenttypes.models import ContentType
    try:
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        model_class = ct.model_class()
    except ContentType.DoesNotExist:
        return Response(
            {"error": f"Model not found: {model_path}"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    fields = []
    for field in model_class._meta.get_fields():
        if not field.is_relation:
            fields.append({
                "name": field.name,
                "verbose_name": getattr(field, "verbose_name", field.name),
                "type": field.get_internal_type(),
                "help_text": getattr(field, "help_text", "")
            })
    
    return Response({
        "model": model_path,
        "fields": fields
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def resolve_device_context_view(request):
    """
    Get the full context available for a device (for debugging/preview).
    
    Query/body params:
    - device_id: Device UUID
    """
    if request.method == "GET":
        device_id = request.query_params.get("device_id")
    else:
        device_id = request.data.get("device_id")
    
    if not device_id:
        return Response(
            {"error": "device_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from nautobot.dcim.models import Device
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return Response(
            {"error": f"Device not found: {device_id}"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    resolver = ContextResolver(device)
    
    return Response({
        "device_id": str(device.pk),
        "device_name": device.name,
        "device_attributes": resolver.get_native_attributes(),
        "config_context": resolver.config_context,
        "local_context_data": resolver.local_context_data
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resolve_variables_view(request):
    """
    Resolve variable mappings for a device.
    
    Request body:
    {
        "device_id": "uuid",
        "variable_mappings": [{"name": "source_interface", "source": "config_context", "path": "ntp.source"}],
        "user_inputs": {"ntp_servers": ["10.0.0.1"]}
    }
    """
    device_id = request.data.get("device_id")
    variable_mappings = request.data.get("variable_mappings", [])
    user_inputs = request.data.get("user_inputs", {})
    
    if not device_id:
        return Response(
            {"error": "device_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from nautobot.dcim.models import Device
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return Response(
            {"error": f"Device not found: {device_id}"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    resolver = ContextResolver(device, overrides=user_inputs)
    result = resolver.resolve(variable_mappings)
    
    return Response({
        "variables": result.get("intended", {}),
        "resolved_details": [],
        "device": result.get("device", {}),
        "config_context": result.get("config_context", {}),
        "local_context_data": result.get("local_context", {})
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def graphql_proxy_view(request):
    """
    Proxy GraphQL queries to Nautobot's GraphQL API.
    
    Request body:
    {
        "query": "query { devices { name } }",
        "variables": {}
    }
    """
    query = request.data.get("query", "")
    variables = request.data.get("variables", {})
    
    if not query:
        return Response(
            {"error": "query is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(query) > 10000:
        return Response(
            {"error": "Query too large"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from nautobot.core.graphql import execute_query
        result = execute_query(query, variables=variables, request=request)
        return Response({
            "data": result.data,
            "errors": [str(e) for e in (result.errors or [])]
        })
    except ImportError:
        return Response(
            {"error": "GraphQL not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def device_search_view(request):
    """
    Search for devices with optional platform filtering.
    
    Query params:
    - q: Search term (matches device name)
    - limit: Max results (default 20, max 100)
    - platform_id: Filter by platform UUID
    - platform_slug: Filter by platform slug
    """
    from nautobot.dcim.models import Device
    
    search_term = request.query_params.get("q", "").strip()
    limit = min(int(request.query_params.get("limit", 20)), 100)
    platform_id = request.query_params.get("platform_id")
    platform_slug = request.query_params.get("platform_slug")
    
    queryset = Device.objects.all()
    
    if search_term:
        queryset = queryset.filter(name__icontains=search_term)
    
    if platform_id:
        queryset = queryset.filter(platform_id=platform_id)
    elif platform_slug:
        queryset = queryset.filter(platform__slug=platform_slug)
    
    queryset = queryset.select_related(
        "platform", "platform__manufacturer", "role", "location"
    ).order_by("name")[:limit]
    
    results = []
    for device in queryset:
        platform_info = None
        if device.platform:
            try:
                platform_info = {
                    "id": str(device.platform.pk),
                    "name": getattr(device.platform, 'name', str(device.platform)),
                    "slug": getattr(device.platform, 'slug', None),
                    "manufacturer": (
                        device.platform.manufacturer.name 
                        if hasattr(device.platform, 'manufacturer') and device.platform.manufacturer 
                        else None
                    )
                }
            except Exception:
                platform_info = {
                    "id": str(device.platform.pk),
                    "name": str(device.platform),
                    "slug": None,
                    "manufacturer": None
                }
        
        results.append({
            "id": str(device.pk),
            "name": device.name,
            "display": str(device),
            "platform": (
                device.platform.name 
                if device.platform and hasattr(device.platform, 'name') 
                else (str(device.platform) if device.platform else None)
            ),
            "platform_info": platform_info,
            "role": (
                device.role.name 
                if device.role and hasattr(device.role, 'name') 
                else (str(device.role) if device.role else None)
            ),
            "location": (
                device.location.name 
                if device.location and hasattr(device.location, 'name') 
                else (str(device.location) if device.location else None)
            )
        })
    
    return Response({
        "results": results,
        "count": len(results)
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def smart_preview_view(request):
    """
    Smart device-based preview that automatically:
    1. Detects device platform
    2. Selects correct strategy (based on platform + priority)
    3. Loads full device context
    4. Renders template with inputs + device context
    
    POST body:
    {
        "task_intent_id": "uuid",
        "device_id": "uuid",
        "variables": {
            "tacacs_servers": ["10.1.1.10", "10.1.1.11"],
            "tacacs_key": "secret123",
            ...
        }
    }
    
    Returns:
    {
        "rendered_content": "...",
        "strategy_used": {...},
        "device_context": {...},
        "variables": {...}
    }
    """
    from nautobot.dcim.models import Device
    from nautobot_network_provisioning.models import TaskIntent
    from jinja2 import Template, TemplateSyntaxError
    import json
    
    task_intent_id = request.data.get("task_intent_id")
    device_id = request.data.get("device_id")
    variables = request.data.get("variables", {})
    
    if not task_intent_id:
        return Response(
            {"error": "task_intent_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not device_id:
        return Response(
            {"error": "device_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        task_intent = TaskIntent.objects.get(pk=task_intent_id)
    except TaskIntent.DoesNotExist:
        return Response(
            {"error": f"TaskIntent with id {task_intent_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        device = Device.objects.select_related(
            "platform", "location", "role", "device_type", "device_type__manufacturer"
        ).prefetch_related("interfaces").get(pk=device_id)
    except Device.DoesNotExist:
        return Response(
            {"error": f"Device with id {device_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Auto-select strategy based on device platform
    if not device.platform:
        return Response(
            {"error": f"Device '{device.name}' has no platform assigned"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Find matching strategies for this platform, ordered by priority
    strategies = task_intent.strategies.filter(
        platform=device.platform
    ).order_by("-priority")
    
    if not strategies.exists():
        return Response(
            {"error": f"No strategy found for platform '{device.platform.name}'"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Use the highest priority strategy
    strategy = strategies.first()
    
    # Build device context (same as what's available in templates)
    device_context = {
        "id": str(device.pk),
        "name": device.name,
        "platform": {
            "name": device.platform.name if device.platform else None,
            "slug": device.platform.slug if device.platform else None,
        },
        "location": {
            "name": device.location.name if device.location else None,
        },
        "role": {
            "name": device.role.name if device.role else None,
        },
        "device_type": {
            "model": device.device_type.model if device.device_type else None,
            "manufacturer": {
                "name": device.device_type.manufacturer.name if device.device_type and device.device_type.manufacturer else None,
            }
        },
        "interfaces": [
            {
                "name": iface.name,
                "type": iface.type,
                "enabled": iface.enabled,
            }
            for iface in device.interfaces.all()[:50]  # Limit to first 50
        ]
    }
    
    # Merge variables with device context
    render_context = {
        "device": device_context,
        **variables
    }
    
    # Add Jinja2 helper functions
    from datetime import datetime
    render_context["now"] = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Render the template
    try:
        template = Template(strategy.template_content or "")
        rendered = template.render(**render_context)
        
        return Response({
            "rendered_content": rendered,
            "strategy_used": {
                "id": str(strategy.pk),
                "name": strategy.name,
                "platform": strategy.platform.name,
                "method": strategy.method,
                "priority": strategy.priority,
            },
            "device_context": device_context,
            "variables": variables,
            "context": render_context  # Full context for debugging
        })
    
    except TemplateSyntaxError as e:
        return Response(
            {
                "error": "Template syntax error",
                "details": str(e),
                "line": e.lineno
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {
                "error": "Rendering failed",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def platform_list_view(request):
    """
    Get list of all platforms for strategy creation.
    """
    from nautobot.dcim.models import Platform
    
    platforms = Platform.objects.all().select_related("manufacturer").order_by("manufacturer__name", "name")
    
    results = []
    for platform in platforms:
        try:
            manufacturer_name = (
                platform.manufacturer.name 
                if platform.manufacturer and hasattr(platform.manufacturer, 'name') 
                else None
            )
            platform_name = getattr(platform, 'name', str(platform))
            platform_slug = getattr(platform, 'slug', None)
            
            results.append({
                "id": str(platform.pk),
                "name": platform_name,
                "slug": platform_slug,
                "manufacturer": manufacturer_name,
                "display": f"{manufacturer_name} {platform_name}" if manufacturer_name else platform_name
            })
        except Exception:
            continue
    
    return Response({
        "results": results,
        "count": len(results)
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def input_types_view(request):
    """
    Get list of available input types for the low-code input builder.
    """
    types = [
        {"value": "string", "label": "Text", "description": "Single line text input"},
        {"value": "text", "label": "Multi-line Text", "description": "Multi-line text area"},
        {"value": "integer", "label": "Number", "description": "Whole number"},
        {"value": "boolean", "label": "Toggle", "description": "Yes/No toggle"},
        {"value": "ip", "label": "IP Address", "description": "IPv4 or IPv6 address"},
        {"value": "cidr", "label": "Network CIDR", "description": "Network in CIDR notation (e.g., 10.0.0.0/24)"},
        {"value": "list[string]", "label": "Text List", "description": "Multiple text values"},
        {"value": "list[ip]", "label": "IP Address List", "description": "Multiple IP addresses"},
        {"value": "device", "label": "Device Selector", "description": "Pick a Nautobot device"},
        {"value": "interface", "label": "Interface Selector", "description": "Pick an interface (filtered by device)"},
        {"value": "vlan_id", "label": "VLAN ID", "description": "VLAN number (1-4094)"},
        {"value": "location", "label": "Location Selector", "description": "Pick a Nautobot location"},
        {"value": "select", "label": "Dropdown", "description": "Choose from a list of options"},
        {"value": "json", "label": "JSON", "description": "Raw JSON data"},
    ]
    
    sources = [
        {"value": "input", "label": "User Input", "description": "User provides this value in the form"},
        {"value": "config_context", "label": "Config Context", "description": "From device/site config context"},
        {"value": "device_attribute", "label": "Device Attribute", "description": "From device model (name, platform, etc.)"},
        {"value": "local_context", "label": "Local Context", "description": "From device local_context_data"},
    ]
    
    return Response({
        "types": types,
        "sources": sources
    })
