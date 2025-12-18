"""URLs for execution actions (Phase 4-5)."""

from django.urls import path

from nautobot_network_provisioning.execution_actions import ExecutionApproveView, ExecutionSetOperationView

urlpatterns = [
    path("executions/<uuid:pk>/approve/", ExecutionApproveView.as_view(), name="execution_approve"),
    path("executions/<uuid:pk>/operation/<str:operation>/", ExecutionSetOperationView.as_view(), name="execution_set_operation"),
]


