from nautobot.apps.filters import NautobotFilterSet
from .models import TaskIntent, Workflow, RequestForm, Execution, AutomationProvider, AutomationProviderConfig, TaskStrategy


class TaskIntentFilterSet(NautobotFilterSet):
    class Meta:
        model = TaskIntent
        fields = ("id", "name", "slug")

class TaskStrategyFilterSet(NautobotFilterSet):
    class Meta:
        model = TaskStrategy
        fields = ("id", "task_intent", "platform", "logic_type", "priority", "enabled")


class WorkflowFilterSet(NautobotFilterSet):
    class Meta:
        model = Workflow
        fields = ("id", "name", "slug")


class RequestFormFilterSet(NautobotFilterSet):
    class Meta:
        model = RequestForm
        fields = ("id", "name", "slug", "workflow")


class ExecutionFilterSet(NautobotFilterSet):
    class Meta:
        model = Execution
        fields = ("id", "workflow", "request_form", "user", "status")


class AutomationProviderFilterSet(NautobotFilterSet):
    class Meta:
        model = AutomationProvider
        fields = ("id", "name", "slug")


class AutomationProviderConfigFilterSet(NautobotFilterSet):
    class Meta:
        model = AutomationProviderConfig
        fields = ("id", "name", "slug", "provider")
