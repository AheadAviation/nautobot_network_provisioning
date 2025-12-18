"""UI URL routes for the Network Provisioning (Automation) app."""

import logging

from nautobot_network_provisioning.execution_action_urls import urlpatterns as execution_action_urlpatterns
from nautobot_network_provisioning.portal_urls import urlpatterns as portal_urlpatterns

logger = logging.getLogger(__name__)

urlpatterns = []
urlpatterns += portal_urlpatterns
urlpatterns += execution_action_urlpatterns

# NOTE: Nautobot core may import plugin URLs very early during startup (including for management commands).
# If the full UI viewsets cannot be imported for any reason, we still want the plugin to load so migrations,
# post_upgrade, etc. can run. UI routes will be unavailable until the import issue is fixed.
try:
    from nautobot.apps.urls import NautobotUIViewSetRouter

    from nautobot_network_provisioning.views import (
        ExecutionUIViewSet,
        ProviderConfigUIViewSet,
        ProviderUIViewSet,
        RequestFormFieldUIViewSet,
        RequestFormUIViewSet,
        TaskDefinitionUIViewSet,
        TaskImplementationUIViewSet,
        WorkflowStepUIViewSet,
        WorkflowUIViewSet,
    )

    router = NautobotUIViewSetRouter()
    router.register("tasks", TaskDefinitionUIViewSet)
    router.register("task-implementations", TaskImplementationUIViewSet)
    router.register("workflows", WorkflowUIViewSet)
    router.register("workflow-steps", WorkflowStepUIViewSet)
    router.register("executions", ExecutionUIViewSet)
    router.register("providers", ProviderUIViewSet)
    router.register("provider-configs", ProviderConfigUIViewSet)
    router.register("request-forms", RequestFormUIViewSet)
    router.register("request-form-fields", RequestFormFieldUIViewSet)

    urlpatterns += router.urls
except Exception:  # noqa: BLE001
    # Intentionally swallow to avoid breaking Nautobot startup/management commands.
    logger.exception("Failed to register nautobot_network_provisioning UI viewset routes; UI links may be invalid.")
    pass


