"""API URL routes for the Network Provisioning (Automation) app."""

from django.urls import path
from nautobot.apps.api import OrderedDefaultRouter

from nautobot_network_provisioning.api.views import (
    ExecutionStepViewSet,
    ExecutionViewSet,
    ProviderConfigViewSet,
    ProviderViewSet,
    RequestFormFieldViewSet,
    RequestFormViewSet,
    TaskDefinitionViewSet,
    TaskImplementationViewSet,
    WorkflowStepViewSet,
    WorkflowViewSet,
    template_preview,
)

router = OrderedDefaultRouter()

router.register("tasks", TaskDefinitionViewSet)
router.register("task-implementations", TaskImplementationViewSet)
router.register("workflows", WorkflowViewSet)
router.register("workflow-steps", WorkflowStepViewSet)
router.register("executions", ExecutionViewSet)
router.register("execution-steps", ExecutionStepViewSet)
router.register("providers", ProviderViewSet)
router.register("provider-configs", ProviderConfigViewSet)
router.register("request-forms", RequestFormViewSet)
router.register("request-form-fields", RequestFormFieldViewSet)

urlpatterns = [
    path("template-preview/", template_preview, name="template-preview"),
]

urlpatterns += router.urls


