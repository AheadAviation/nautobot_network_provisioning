"""Tables for the Network Provisioning (Automation) app."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn, ToggleColumn

from nautobot_network_provisioning.models import (
    Execution,
    Provider,
    ProviderConfig,
    RequestForm,
    RequestFormField,
    TaskDefinition,
    TaskImplementation,
    Workflow,
    WorkflowStep,
)


class TaskDefinitionTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    slug = tables.Column()
    category = tables.Column()
    vendors = tables.TemplateColumn(
        template_code='{% for m in record.implementations.all %}{{ m.manufacturer }}{% if not forloop.last %}, {% endif %}{% empty %}None{% endfor %}',
        orderable=False
    )
    actions = ButtonsColumn(TaskDefinition)

    class Meta(BaseTable.Meta):
        model = TaskDefinition
        fields = ("pk", "name", "slug", "category", "vendors", "actions")
        default_columns = fields


class TaskImplementationTable(BaseTable):
    pk = ToggleColumn()
    task = tables.LinkColumn()
    name = tables.LinkColumn()
    manufacturer = tables.LinkColumn()
    platform = tables.LinkColumn()
    software_versions = tables.Column(verbose_name="Software Versions", accessor="software_versions", orderable=False)
    implementation_type = tables.Column()
    enabled = tables.BooleanColumn()
    actions = ButtonsColumn(TaskImplementation)

    class Meta(BaseTable.Meta):
        model = TaskImplementation
        fields = (
            "pk",
            "task",
            "name",
            "manufacturer",
            "platform",
            "software_versions",
            "priority",
            "implementation_type",
            "enabled",
            "actions",
        )
        default_columns = ("pk", "task", "name", "manufacturer", "platform", "priority", "enabled", "actions")


class WorkflowTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    slug = tables.Column()
    enabled = tables.BooleanColumn()
    approval_required = tables.BooleanColumn()
    schedule_allowed = tables.BooleanColumn()
    actions = ButtonsColumn(Workflow)

    class Meta(BaseTable.Meta):
        model = Workflow
        fields = ("pk", "name", "slug", "enabled", "approval_required", "schedule_allowed", "actions")
        default_columns = fields


class WorkflowStepTable(BaseTable):
    pk = ToggleColumn()
    workflow = tables.LinkColumn()
    name = tables.LinkColumn()
    step_type = tables.Column()
    order = tables.Column()
    task = tables.LinkColumn()
    actions = ButtonsColumn(WorkflowStep)

    class Meta(BaseTable.Meta):
        model = WorkflowStep
        fields = ("pk", "workflow", "order", "name", "step_type", "task", "actions")
        default_columns = fields


class ExecutionTable(BaseTable):
    pk = ToggleColumn()
    workflow = tables.LinkColumn()
    status = tables.Column()
    created = tables.DateTimeColumn()
    actions = ButtonsColumn(Execution)

    class Meta(BaseTable.Meta):
        model = Execution
        fields = ("pk", "workflow", "status", "scheduled_for", "created", "actions")
        default_columns = fields


class ProviderTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    enabled = tables.BooleanColumn()
    actions = ButtonsColumn(Provider)

    class Meta(BaseTable.Meta):
        model = Provider
        fields = ("pk", "name", "driver_class", "enabled", "actions")
        default_columns = ("pk", "name", "driver_class", "enabled", "actions")


class ProviderConfigTable(BaseTable):
    pk = ToggleColumn()
    provider = tables.LinkColumn()
    name = tables.LinkColumn()
    enabled = tables.BooleanColumn()
    actions = ButtonsColumn(ProviderConfig)

    class Meta(BaseTable.Meta):
        model = ProviderConfig
        fields = ("pk", "provider", "name", "enabled", "actions")
        default_columns = fields


class RequestFormTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    slug = tables.Column()
    workflow = tables.LinkColumn()
    published = tables.BooleanColumn()
    actions = ButtonsColumn(RequestForm)

    class Meta(BaseTable.Meta):
        model = RequestForm
        fields = ("pk", "name", "slug", "workflow", "published", "actions")
        default_columns = fields


class RequestFormFieldTable(BaseTable):
    pk = ToggleColumn()
    form = tables.LinkColumn()
    order = tables.Column()
    field_name = tables.Column()
    label = tables.Column()
    field_type = tables.Column()
    lookup = tables.TemplateColumn(
        template_code='''
        {% if record.lookup_type == "manual" %}
            <span class="label label-default">Manual</span>
        {% else %}
            <span class="label label-info">{{ record.get_lookup_type_display }}</span>
            <br><small class="text-muted">{{ record.lookup_config }}</small>
        {% endif %}
        ''',
        verbose_name="Lookup/Filter"
    )
    required = tables.BooleanColumn()
    actions = ButtonsColumn(RequestFormField)

    class Meta(BaseTable.Meta):
        model = RequestFormField
        fields = ("pk", "form", "order", "field_name", "label", "field_type", "lookup", "required", "actions")
        default_columns = fields


