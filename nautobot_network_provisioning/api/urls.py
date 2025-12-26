"""
API URL Configuration v2.0

Includes TaskStrategy endpoints and enhanced utility endpoints.
"""
from django.urls import path
from nautobot.apps.api import OrderedDefaultRouter
from . import views

router = OrderedDefaultRouter()

# ═══════════════════════════════════════════════════════════════════════════
# MODEL VIEWSETS
# ═══════════════════════════════════════════════════════════════════════════
router.register("task-intents", views.TaskIntentViewSet)
router.register("task-strategies", views.TaskStrategyViewSet)
router.register("workflows", views.WorkflowViewSet)
router.register("folders", views.FolderViewSet)
router.register("request-forms", views.RequestFormViewSet)
router.register("executions", views.ExecutionViewSet)

# ═══════════════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════
urlpatterns = [
    # Template validation and preview
    path("validate-task/", views.validate_task, name="validate_task"),
    path("template-preview/", views.template_preview, name="template_preview"),
    path("render-preview/", views.render_preview, name="render_preview"),
    path("preview/", views.render_preview, name="preview"),  # Alias for frontend compatibility
    path("smart-preview/", views.smart_preview_view, name="smart_preview"),  # NEW: Auto-select strategy based on device
    
    # Context and variable resolution
    path("resolve-device-context/", views.resolve_device_context_view, name="resolve_device_context"),
    path("resolve-variables/", views.resolve_variables_view, name="resolve_variables"),
    
    # Model and metadata
    path("model-metadata/", views.model_metadata, name="model_metadata"),
    path("input-types/", views.input_types_view, name="input_types"),  # NEW: For low-code input builder
    
    # Search and lookup
    path("device-search/", views.device_search_view, name="device_search"),
    path("platforms/", views.platform_list_view, name="platform_list"),
    
    # GraphQL proxy
    path("graphql-proxy/", views.graphql_proxy_view, name="graphql_proxy"),
]

urlpatterns += router.urls
