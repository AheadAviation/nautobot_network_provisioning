from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
import json
from nautobot.apps.views import NautobotUIViewSet
from . import models
from . import tables
from . import filters


@method_decorator(login_required, name='dispatch')
class StudioShellView(View):
    """
    StudioShell v4.0 - Multi-Modal IDE Entry Point
    
    This is the root view that loads the StudioShell architecture with Activity Bar
    and mode switching. Individual modes are loaded via client-side routing.
    """
    template_name = "nautobot_network_provisioning/studio_shell.html"
    
    def get(self, request, mode='library', item_type=None, pk=None):
        """
        mode: 'library', 'code', 'flow', 'ui'
        item_type: 'task', 'workflow', 'form' (for deep linking)
        pk: UUID of item to load
        """
        # Prepare data for all modes
        context = {
            "mode": mode,
            "item_type": item_type,
            "item_id": str(pk) if pk else None,
        }
        
        # Load specific item data if provided
        if pk and item_type == 'task':
            task_intent = get_object_or_404(models.TaskIntent, pk=pk)
            from .api.serializers import TaskIntentSerializer
            from rest_framework.renderers import JSONRenderer
            serializer = TaskIntentSerializer(task_intent, context={"request": request})
            context["task_json"] = JSONRenderer().render(serializer.data).decode("utf-8")
            context["object"] = task_intent
        elif pk and item_type == 'workflow':
            workflow = get_object_or_404(models.Workflow, pk=pk)
            context["workflow_json"] = json.dumps({
                "id": str(workflow.pk),
                "name": workflow.name,
                "slug": workflow.slug,
                "graph_definition": workflow.graph_definition or {},
            }, default=str)
            context["object"] = workflow
        elif pk and item_type == 'form':
            request_form = get_object_or_404(models.RequestForm, pk=pk)
            context["form_json"] = json.dumps({
                "id": str(request_form.pk),
                "name": request_form.name,
                "slug": request_form.slug,
            }, default=str)
            context["object"] = request_form
        else:
            context["task_json"] = "{}"
            context["workflow_json"] = "{}"
            context["form_json"] = "{}"
            context["object"] = None
        
        return render(request, self.template_name, context)


# UI ViewSets for NautobotUIViewSetRouter
# These provide standard CRUD operations for the web UI

class TaskIntentUIViewSet(NautobotUIViewSet):
    queryset = models.TaskIntent.objects.all()
    filterset_class = filters.TaskIntentFilterSet
    form_class = None  # Using custom Studio interface, not standard forms
    table_class = tables.TaskIntentTable


class TaskStrategyUIViewSet(NautobotUIViewSet):
    """UI ViewSet for TaskStrategy (platform-specific implementations)."""
    queryset = models.TaskStrategy.objects.all()
    filterset_class = filters.TaskStrategyFilterSet
    form_class = None  # Using custom Studio interface, not standard forms
    table_class = tables.TaskStrategyTable


class WorkflowUIViewSet(NautobotUIViewSet):
    queryset = models.Workflow.objects.all()
    filterset_class = filters.WorkflowFilterSet
    form_class = None  # Using custom Studio interface, not standard forms
    table_class = tables.WorkflowTable


class RequestFormUIViewSet(NautobotUIViewSet):
    queryset = models.RequestForm.objects.all()
    filterset_class = filters.RequestFormFilterSet
    form_class = None  # Using custom Studio interface, not standard forms
    table_class = tables.RequestFormTable


class ExecutionUIViewSet(NautobotUIViewSet):
    queryset = models.Execution.objects.all()
    filterset_class = filters.ExecutionFilterSet
    form_class = None  # Read-only viewset for execution history
    table_class = tables.ExecutionTable


class AutomationProviderUIViewSet(NautobotUIViewSet):
    queryset = models.AutomationProvider.objects.all()
    filterset_class = filters.AutomationProviderFilterSet
    form_class = None
    table_class = tables.AutomationProviderTable


class AutomationProviderConfigUIViewSet(NautobotUIViewSet):
    queryset = models.AutomationProviderConfig.objects.all()
    filterset_class = filters.AutomationProviderConfigFilterSet
    form_class = None
    table_class = tables.AutomationProviderConfigTable


# Placeholder views for Studio interfaces (to be implemented)

@method_decorator(login_required, name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class WorkflowDesignerView(View):
    """
    Workflow Orchestrator - React Flow Canvas
    
    Note: @xframe_options_exempt allows this view to be embedded in iframes
    within the StudioShell interface.
    """
    template_name = "nautobot_network_provisioning/workflow_orchestrator.html"
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to ensure X-Frame-Options is not set"""
        response = super().dispatch(request, *args, **kwargs)
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        return response
    
    def get(self, request, pk=None):
        if pk:
            workflow = get_object_or_404(models.Workflow, pk=pk)
        else:
            workflow = None
        
        # Prepare workflow data for JS
        workflow_json = "{}"
        if workflow:
            workflow_json = json.dumps({
                "id": str(workflow.pk),
                "name": workflow.name,
                "slug": workflow.slug,
                "graph_definition": workflow.graph_definition or {},
            }, default=str)

        context = {
            "object": workflow,
            "workflow_json": workflow_json,
        }
        return render(request, self.template_name, context)


class ExecutionRunView(View):
    """Execution Trigger View - placeholder"""
    
    def post(self, request, pk):
        execution = get_object_or_404(models.Execution, pk=pk)
        # TODO: Implement execution trigger logic
        return redirect("plugins:nautobot_network_provisioning:execution_detail", pk=pk)


@method_decorator(login_required, name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class TaskStudioV2View(View):
    """
    Task Studio v2.0 - Low-Code First Architecture
    
    Three-zone layout:
    - Zone A (Left): Input variable builder
    - Zone B (Center): Strategy editor with multi-method support
    - Zone C (Right): Live preview with device context
    
    Features:
    - Low-code input builder with smart types
    - Multi-method strategies (CLI, REST API, NETCONF, etc.)
    - YAML export for Git storage
    - Real-time template preview
    
    Note: @xframe_options_exempt allows this view to be embedded in iframes
    within the StudioShell interface.
    """
    template_name = "nautobot_network_provisioning/task_studio_v2.html"
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to ensure X-Frame-Options is not set"""
        response = super().dispatch(request, *args, **kwargs)
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        return response
    
    def get(self, request, pk=None):
        if pk:
            task_intent = get_object_or_404(models.TaskIntent, pk=pk)
        else:
            task_intent = None
        
        # Prepare task data for JS
        task_json = "{}"
        if task_intent:
            from .api.serializers import TaskIntentSerializer
            from rest_framework.renderers import JSONRenderer
            serializer = TaskIntentSerializer(task_intent, context={"request": request})
            task_json = JSONRenderer().render(serializer.data).decode("utf-8")

        context = {
            "object": task_intent,
            "task_json": task_json,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class FormDesignerView(View):
    """
    Form Designer - Drag-and-drop builder for request forms
    
    Note: @xframe_options_exempt allows this view to be embedded in iframes
    within the StudioShell interface.
    """
    template_name = "nautobot_network_provisioning/form_designer.html"
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to ensure X-Frame-Options is not set"""
        response = super().dispatch(request, *args, **kwargs)
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        return response
    
    def get(self, request, pk=None):
        if pk:
            request_form = get_object_or_404(models.RequestForm, pk=pk)
        else:
            request_form = None
        
        # Prepare form data for JS
        form_json = "{}"
        if request_form:
            form_json = json.dumps({
                "id": str(request_form.pk),
                "name": request_form.name,
                "slug": request_form.slug,
                "workflow_id": str(request_form.workflow_id) if request_form.workflow_id else None,
                "field_definition": request_form.field_definition or {},
            }, default=str)

        context = {
            "object": request_form,
            "form_json": form_json,
        }
        return render(request, self.template_name, context)