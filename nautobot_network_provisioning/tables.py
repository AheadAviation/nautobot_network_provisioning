"""Tables for the NetAccess app."""

import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from nautobot.apps.tables import BaseTable, ToggleColumn, ButtonsColumn

from nautobot_network_provisioning.models import (
    PortService,
    SwitchProfile,
    ConfigTemplate,
    JackMapping,
    WorkQueueEntry,
    MACAddress,
    MACAddressEntry,
    MACAddressHistory,
    ARPEntry,
    ControlSetting,
)


class PortServiceTable(BaseTable):
    """Table for displaying Automated Task instances (formerly Port Services)."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    template_count = tables.Column(
        accessor="template_count",
        verbose_name="Templates",
        orderable=False,
    )
    is_active = tables.BooleanColumn()
    actions = ButtonsColumn(PortService)

    class Meta(BaseTable.Meta):
        model = PortService
        fields = ("pk", "name", "description", "template_count", "is_active", "actions")
        default_columns = ("pk", "name", "description", "template_count", "is_active", "actions")


class SwitchProfileTable(BaseTable):
    """Table for displaying SwitchProfile instances."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    platform = tables.LinkColumn()
    actions = ButtonsColumn(SwitchProfile)

    class Meta(BaseTable.Meta):
        model = SwitchProfile
        fields = (
            "pk",
            "name",
            "device_type_pattern",
            "os_version_pattern",
            "platform",
            "priority",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "device_type_pattern",
            "os_version_pattern",
            "priority",
            "actions",
        )


class TemplatePreviewColumn(tables.Column):
    """Custom column to show a preview of the template text."""
    
    def render(self, value):
        if not value:
            return "-"
        # Show first 200 chars with syntax highlighting hint
        preview = value[:200].strip()
        if len(value) > 200:
            preview += "..."
        # Escape HTML and wrap in code block
        escaped = preview.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return format_html(
            '<pre class="template-preview" style="font-size: 11px; margin: 0; max-height: 80px; '
            'overflow: hidden; background: #f5f5f5; padding: 4px; border-radius: 4px; '
            'white-space: pre-wrap; word-break: break-word;"><code>{}</code></pre>',
            mark_safe(escaped)
        )


class SoftwareVersionsColumn(tables.Column):
    """Custom column to display multiple software versions."""
    
    def render(self, value):
        versions = list(value.all())
        if not versions:
            return format_html('<span class="text-muted">All versions</span>')
        if len(versions) <= 3:
            return ", ".join(str(v) for v in versions)
        return format_html(
            '{}, ... <span class="badge bg-info">+{} more</span>',
            ", ".join(str(v) for v in versions[:2]),
            len(versions) - 2
        )


class ConfigTemplateTable(BaseTable):
    """Table for displaying ConfigTemplate instances with template preview."""

    pk = ToggleColumn()
    service = tables.LinkColumn(verbose_name="Task")
    manufacturer = tables.LinkColumn()
    platform = tables.LinkColumn()
    software_versions = SoftwareVersionsColumn(
        accessor="software_versions",
        verbose_name="Software Versions",
        orderable=False,
    )
    template_preview = TemplatePreviewColumn(
        accessor="template_text",
        verbose_name="Template Preview",
        orderable=False,
    )
    is_active = tables.BooleanColumn()
    effective_date = tables.DateColumn()
    actions = ButtonsColumn(ConfigTemplate)

    class Meta(BaseTable.Meta):
        model = ConfigTemplate
        fields = (
            "pk",
            "service",
            "manufacturer",
            "platform",
            "software_versions",
            "template_preview",
            "effective_date",
            "version",
            "is_active",
            "created_by",
            "actions",
        )
        default_columns = (
            "pk",
            "service",
            "manufacturer",
            "platform",
            "software_versions",
            "template_preview",
            "is_active",
            "actions",
        )


class JackMappingTable(BaseTable):
    """Table for displaying JackMapping instances."""

    pk = ToggleColumn()
    building = tables.LinkColumn()
    device = tables.LinkColumn()
    interface = tables.LinkColumn()
    is_active = tables.BooleanColumn()
    actions = ButtonsColumn(JackMapping)

    class Meta(BaseTable.Meta):
        model = JackMapping
        fields = (
            "pk",
            "building",
            "comm_room",
            "jack",
            "device",
            "interface",
            "is_active",
            "actions",
        )
        default_columns = (
            "pk",
            "building",
            "comm_room",
            "jack",
            "device",
            "interface",
            "is_active",
            "actions",
        )


class WorkQueueEntryTable(BaseTable):
    """
    Table for displaying WorkQueueEntry instances.
    
    Enhanced TWIX-style table with full columns matching original TWIX show-orders.py:
    - Building, Comm Room, Jack context
    - Switch Name, Switch Port
    - Request Date, Requested By
    - Date Scheduled, Date of Last Attempt
    - Status with color badges
    - Status Message (expandable)
    """

    pk = ToggleColumn()
    
    # Building/Room/Jack columns
    building = tables.Column(
        accessor="building.name",
        verbose_name="Building",
        orderable=True,
    )
    comm_room = tables.Column(
        verbose_name="Comm Room",
        orderable=True,
    )
    jack = tables.Column(
        verbose_name="Jack",
        orderable=True,
    )
    
    # Switch/Port columns
    device = tables.LinkColumn(
        verbose_name="Switch",
    )
    interface = tables.LinkColumn(
        verbose_name="Port",
    )
    
    # Service column
    service = tables.LinkColumn(
        verbose_name="Service",
    )
    
    # Status with color badges
    status = tables.TemplateColumn(
        verbose_name="Status",
        template_code="""
        {% if record.status == 'pending' %}
            <span class="badge bg-warning text-dark">
                <i class="mdi mdi-clock-outline"></i> Pending
            </span>
        {% elif record.status == 'in_progress' %}
            <span class="badge bg-info">
                <i class="mdi mdi-progress-clock"></i> In Progress
            </span>
        {% elif record.status == 'completed' %}
            <span class="badge bg-success">
                <i class="mdi mdi-check-circle"></i> Completed
            </span>
        {% elif record.status == 'failed' %}
            <span class="badge bg-danger">
                <i class="mdi mdi-alert-circle"></i> Failed
            </span>
        {% elif record.status == 'cancelled' %}
            <span class="badge bg-secondary">
                <i class="mdi mdi-cancel"></i> Cancelled
            </span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.get_status_display }}</span>
        {% endif %}
        """
    )
    
    # Date columns
    scheduled_time = tables.DateTimeColumn(
        verbose_name="Scheduled",
        format="Y-m-d H:i",
    )
    created = tables.DateTimeColumn(
        verbose_name="Requested",
        format="Y-m-d H:i",
    )
    attempted_time = tables.DateTimeColumn(
        verbose_name="Last Attempt",
        format="Y-m-d H:i",
    )
    completed_time = tables.DateTimeColumn(
        verbose_name="Completed",
        format="Y-m-d H:i",
    )
    
    # User column
    requested_by = tables.Column(
        verbose_name="Requested By",
        orderable=True,
    )
    
    # Status message (truncated with tooltip)
    status_message = tables.TemplateColumn(
        verbose_name="Message",
        template_code="""
        {% if record.status_message %}
            <span title="{{ record.status_message }}" 
                  data-bs-toggle="tooltip"
                  style="cursor: pointer;">
                {{ record.status_message|truncatewords:10 }}
            </span>
        {% else %}
            <span class="text-muted">—</span>
        {% endif %}
        """
    )
    
    actions = ButtonsColumn(WorkQueueEntry)

    class Meta(BaseTable.Meta):
        model = WorkQueueEntry
        fields = (
            "pk",
            "building",
            "comm_room",
            "jack",
            "device",
            "interface",
            "service",
            "scheduled_time",
            "status",
            "status_message",
            "requested_by",
            "created",
            "attempted_time",
            "completed_time",
            "actions",
        )
        default_columns = (
            "pk",
            "building",
            "comm_room",
            "jack",
            "device",
            "interface",
            "service",
            "scheduled_time",
            "status",
            "requested_by",
            "actions",
        )


class MACAddressTable(BaseTable):
    """Table for displaying MACAddress instances."""

    pk = ToggleColumn()
    address = tables.LinkColumn()
    mac_type = tables.TemplateColumn(
        template_code="{{ record.get_mac_type_display }}"
    )
    last_device = tables.LinkColumn()
    last_interface = tables.LinkColumn()
    actions = ButtonsColumn(MACAddress)

    class Meta(BaseTable.Meta):
        model = MACAddress
        fields = (
            "pk",
            "address",
            "mac_type",
            "vendor",
            "last_device",
            "last_interface",
            "last_vlan",
            "last_ip",
            "last_seen",
            "actions",
        )
        default_columns = (
            "pk",
            "address",
            "mac_type",
            "vendor",
            "last_device",
            "last_interface",
            "last_seen",
            "actions",
        )


class MACAddressEntryTable(BaseTable):
    """Table for displaying MACAddressEntry instances."""

    pk = ToggleColumn()
    mac_address = tables.LinkColumn()
    device = tables.LinkColumn()
    interface = tables.LinkColumn()
    entry_type = tables.TemplateColumn(
        template_code="{{ record.get_entry_type_display }}"
    )

    class Meta(BaseTable.Meta):
        model = MACAddressEntry
        fields = (
            "pk",
            "mac_address",
            "device",
            "interface",
            "vlan",
            "entry_type",
            "collected_time",
        )
        default_columns = (
            "pk",
            "mac_address",
            "device",
            "interface",
            "vlan",
            "entry_type",
            "collected_time",
        )


class MACAddressHistoryTable(BaseTable):
    """Table for displaying MACAddressHistory instances."""

    pk = ToggleColumn()
    mac_address = tables.LinkColumn()
    device = tables.LinkColumn()
    interface = tables.LinkColumn()

    class Meta(BaseTable.Meta):
        model = MACAddressHistory
        fields = (
            "pk",
            "mac_address",
            "device",
            "interface",
            "vlan",
            "entry_type",
            "first_seen",
            "last_seen",
            "sighting_count",
        )
        default_columns = (
            "pk",
            "mac_address",
            "device",
            "interface",
            "vlan",
            "first_seen",
            "last_seen",
            "sighting_count",
        )


class ARPEntryTable(BaseTable):
    """Table for displaying ARPEntry instances."""

    pk = ToggleColumn()
    mac_address = tables.LinkColumn()
    device = tables.LinkColumn()
    interface = tables.LinkColumn()
    entry_type = tables.TemplateColumn(
        template_code="{{ record.get_entry_type_display }}"
    )

    class Meta(BaseTable.Meta):
        model = ARPEntry
        fields = (
            "pk",
            "ip_address",
            "mac_address",
            "device",
            "interface",
            "vrf",
            "entry_type",
            "collected_time",
        )
        default_columns = (
            "pk",
            "ip_address",
            "mac_address",
            "device",
            "interface",
            "vrf",
            "entry_type",
            "collected_time",
        )


class ControlSettingTable(BaseTable):
    """Table for displaying ControlSetting instances."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    actions = ButtonsColumn(ControlSetting)

    class Meta(BaseTable.Meta):
        model = ControlSetting
        fields = ("pk", "name", "value", "description", "actions")
        default_columns = ("pk", "name", "value", "description", "actions")
