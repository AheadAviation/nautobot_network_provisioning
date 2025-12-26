"""
Table definitions for Network Provisioning Plugin v2.0

Defines django-tables2 tables for list views in the Nautobot UI.
"""
import django_tables2 as tables
from django.utils.html import format_html
from nautobot.apps.tables import BaseTable, ButtonsColumn
from .models import (
    TaskIntent, 
    TaskStrategy,
    Workflow, 
    RequestForm, 
    Execution, 
    AutomationProvider, 
    AutomationProviderConfig, 
    Folder
)


class StudioLinkColumn(tables.Column):
    """Custom column that links to the Task Studio editor."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("verbose_name", "Studio")
        kwargs.setdefault("orderable", False)
        kwargs.setdefault("empty_values", ())
        super().__init__(*args, **kwargs)
    
    def render(self, record):
        from django.urls import reverse
        url = reverse("plugins:nautobot_network_provisioning:task_studio_v2_edit", kwargs={"pk": record.pk})
        return format_html(
            '<a href="{}" class="btn btn-xs btn-primary" title="Edit in Studio v2">'
            '<i class="mdi mdi-pencil-box-outline"></i> Studio'
            '</a>',
            url
        )


class TaskIntentTable(BaseTable):
    """Table for TaskIntent list view."""
    pk = tables.CheckBoxColumn()
    name = tables.Column(linkify=True)
    category = tables.Column()
    strategy_count = tables.Column(verbose_name="Strategies", accessor="strategy_count", orderable=False)
    input_count = tables.Column(verbose_name="Inputs", accessor="input_count", orderable=False)
    studio = StudioLinkColumn()
    actions = ButtonsColumn(TaskIntent)

    class Meta(BaseTable.Meta):
        model = TaskIntent
        fields = ("pk", "name", "slug", "category", "input_count", "strategy_count", "description", "studio", "actions")


class TaskStrategyTable(BaseTable):
    """Table for TaskStrategy list view (the new primary implementation model)."""
    pk = tables.CheckBoxColumn()
    task_intent = tables.Column(linkify=True)
    platform = tables.Column(linkify=True)
    method = tables.Column(verbose_name="Method")
    priority = tables.Column()
    enabled = tables.BooleanColumn()
    actions = ButtonsColumn(TaskStrategy)

    class Meta(BaseTable.Meta):
        model = TaskStrategy
        fields = ("pk", "task_intent", "platform", "method", "priority", "enabled", "actions")


class WorkflowTable(BaseTable):
    """Table for Workflow list view."""
    pk = tables.CheckBoxColumn()
    name = tables.Column(linkify=True)
    enabled = tables.BooleanColumn()
    actions = ButtonsColumn(Workflow)

    class Meta(BaseTable.Meta):
        model = Workflow
        fields = ("pk", "name", "description", "enabled", "actions")


class RequestFormTable(BaseTable):
    """Table for RequestForm list view."""
    pk = tables.CheckBoxColumn()
    name = tables.Column(linkify=True)
    workflow = tables.Column(linkify=True)
    published = tables.BooleanColumn()
    actions = ButtonsColumn(RequestForm)

    class Meta(BaseTable.Meta):
        model = RequestForm
        fields = ("pk", "name", "workflow", "published", "description", "actions")


class ExecutionTable(BaseTable):
    """Table for Execution list view."""
    pk = tables.CheckBoxColumn()
    id = tables.Column(linkify=True)
    workflow = tables.Column(linkify=True)
    status = tables.Column()
    start_time = tables.DateTimeColumn()
    actions = ButtonsColumn(Execution)

    class Meta(BaseTable.Meta):
        model = Execution
        fields = ("pk", "id", "workflow", "status", "user", "start_time", "actions")


class AutomationProviderTable(BaseTable):
    """Table for AutomationProvider list view."""
    pk = tables.CheckBoxColumn()
    name = tables.Column(linkify=True)
    enabled = tables.BooleanColumn()
    actions = ButtonsColumn(AutomationProvider)

    class Meta(BaseTable.Meta):
        model = AutomationProvider
        fields = ("pk", "name", "description", "enabled", "actions")


class AutomationProviderConfigTable(BaseTable):
    """Table for AutomationProviderConfig list view."""
    pk = tables.CheckBoxColumn()
    name = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    enabled = tables.BooleanColumn()
    actions = ButtonsColumn(AutomationProviderConfig)

    class Meta(BaseTable.Meta):
        model = AutomationProviderConfig
        fields = ("pk", "name", "provider", "enabled", "description", "actions")


class FolderTable(BaseTable):
    """Table for Folder list view."""
    pk = tables.CheckBoxColumn()
    name = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    actions = ButtonsColumn(Folder)

    class Meta(BaseTable.Meta):
        model = Folder
        fields = ("pk", "name", "slug", "parent", "description", "actions")
