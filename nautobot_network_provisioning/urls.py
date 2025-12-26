"""
URL Configuration for Network Provisioning Plugin v2.0

Includes:
- Portal views for end users
- Studio views for task/workflow/form authoring
- API endpoints
- Troubleshooting tools
"""
from django.urls import path, include
from nautobot.apps.urls import NautobotUIViewSetRouter
from . import views, portal_views, troubleshooting_views

# ═══════════════════════════════════════════════════════════════════════════
# VIEWSET ROUTER (Standard Nautobot CRUD Views)
# ═══════════════════════════════════════════════════════════════════════════
router = NautobotUIViewSetRouter()
router.register("task-intents", views.TaskIntentUIViewSet)
router.register("task-strategies", views.TaskStrategyUIViewSet)
router.register("workflows", views.WorkflowUIViewSet)
router.register("request-forms", views.RequestFormUIViewSet)
router.register("executions", views.ExecutionUIViewSet)
router.register("automation-providers", views.AutomationProviderUIViewSet)
router.register("automation-provider-configs", views.AutomationProviderConfigUIViewSet)

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════════════
    # PORTAL VIEWS (End User Experience)
    # ═══════════════════════════════════════════════════════════════════════
    path("portal/", portal_views.PortalView.as_view(), name="portal"),
    path("portal/<slug:slug>/", portal_views.PortalRequestFormView.as_view(), name="portal_request_form"),
    
    # ═══════════════════════════════════════════════════════════════════════
    # TASK STUDIO v2 (Low-Code Task Editor)
    # ═══════════════════════════════════════════════════════════════════════
    path("studio/v2/tasks/", views.TaskStudioV2View.as_view(), name="task_studio_v2"),
    path("studio/v2/tasks/<uuid:pk>/", views.TaskStudioV2View.as_view(), name="task_studio_v2_edit"),
    
    # Legacy route aliases for backwards compatibility (redirect to v2)
    path("studio/tasks/", views.TaskStudioV2View.as_view(), name="taskintent_studio"),
    path("studio/tasks/<uuid:pk>/", views.TaskStudioV2View.as_view(), name="taskintent_studio_edit"),
    
    # ═══════════════════════════════════════════════════════════════════════
    # WORKFLOW & FORM DESIGNERS
    # ═══════════════════════════════════════════════════════════════════════
    path("studio/workflows/", views.WorkflowDesignerView.as_view(), name="workflow_studio"),
    path("studio/workflows/<uuid:pk>/", views.WorkflowDesignerView.as_view(), name="workflow_studio_edit"),
    
    path("studio/forms/", views.FormDesignerView.as_view(), name="form_studio"),
    path("studio/forms/<uuid:pk>/", views.FormDesignerView.as_view(), name="form_studio_edit"),

    # ═══════════════════════════════════════════════════════════════════════
    # STUDIO TOOLS (Embedded SPA Islands)
    # ═══════════════════════════════════════════════════════════════════════
    path("studio/tools/troubleshooting/", troubleshooting_views.StudioTroubleshootingLauncherView.as_view(), name="studio_tool_troubleshooting"),
    
    # Troubleshooting API endpoints
    path("api/troubleshooting/run/", troubleshooting_views.TroubleshootingRunAPIView.as_view(), name="api_troubleshooting_run"),
    path("api/troubleshooting/status/<uuid:pk>/", troubleshooting_views.TroubleshootingStatusAPIView.as_view(), name="api_troubleshooting_status"),
    path("api/troubleshooting/history/", troubleshooting_views.TroubleshootingHistoryAPIView.as_view(), name="api_troubleshooting_history"),
    
    # ═══════════════════════════════════════════════════════════════════════
    # STUDIO SHELL v4.0 (Multi-Modal IDE Entry Point)
    # Generic routes MUST come AFTER specific routes!
    # ═══════════════════════════════════════════════════════════════════════
    path("studio/", views.StudioShellView.as_view(), name="studio_shell"),
    path("studio/<str:mode>/", views.StudioShellView.as_view(), name="studio_shell_mode"),
    path("studio/<str:mode>/<str:item_type>/<uuid:pk>/", views.StudioShellView.as_view(), name="studio_shell_item"),

    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTION & TROUBLESHOOTING
    # ═══════════════════════════════════════════════════════════════════════
    path("executions/<uuid:pk>/run/", views.ExecutionRunView.as_view(), name="execution_run"),
    path("troubleshooting/<str:model_label>/<uuid:pk>/", troubleshooting_views.TroubleshootingView.as_view(), name="troubleshooting"),
    path("troubleshooting/visual/<uuid:pk>/", troubleshooting_views.TroubleshootingVisualView.as_view(), name="troubleshooting_visual"),

    # ═══════════════════════════════════════════════════════════════════════
    # API ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════
    path("api/", include("nautobot_network_provisioning.api.urls")),
]

urlpatterns += router.urls
