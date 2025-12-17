"""FilterSets for the NetAccess app."""

import django_filters
from nautobot.apps.filters import NautobotFilterSet, SearchFilter
from nautobot.dcim.models import Device, Interface, Location, Platform, Manufacturer, SoftwareVersion

from nautobot_network_provisioning.models import (
    PortService,
    SwitchProfile,
    ConfigTemplate,
    ConfigTemplateHistory,
    JackMapping,
    WorkQueueEntry,
    MACAddress,
    MACAddressEntry,
    MACAddressHistory,
    ARPEntry,
    ControlSetting,
)


class PortServiceFilterSet(NautobotFilterSet):
    """FilterSet for PortService model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = PortService
        fields = ["id", "name", "is_active"]


class SwitchProfileFilterSet(NautobotFilterSet):
    """FilterSet for SwitchProfile model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "device_type_pattern": "icontains",
            "os_version_pattern": "icontains",
        },
    )
    platform = django_filters.ModelMultipleChoiceFilter(
        queryset=Platform.objects.all(),
    )

    class Meta:
        model = SwitchProfile
        fields = ["id", "name", "platform", "priority"]


class ConfigTemplateFilterSet(NautobotFilterSet):
    """FilterSet for ConfigTemplate model."""

    q = SearchFilter(
        filter_predicates={
            "template_text": "icontains",
            "created_by": "icontains",
        },
    )
    service = django_filters.ModelMultipleChoiceFilter(
        queryset=PortService.objects.all(),
    )
    manufacturer = django_filters.ModelMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(),
    )
    platform = django_filters.ModelMultipleChoiceFilter(
        queryset=Platform.objects.all(),
    )
    software_versions = django_filters.ModelMultipleChoiceFilter(
        queryset=SoftwareVersion.objects.all(),
        field_name="software_versions",
    )
    is_active = django_filters.BooleanFilter()
    effective_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = ConfigTemplate
        fields = [
            "id",
            "service",
            "manufacturer",
            "platform",
            "software_versions",
            "is_active",
            "effective_date",
            "version",
        ]


class ConfigTemplateHistoryFilterSet(NautobotFilterSet):
    """FilterSet for ConfigTemplateHistory model."""

    q = SearchFilter(
        filter_predicates={
            "template_text": "icontains",
            "changed_by": "icontains",
            "change_reason": "icontains",
        },
    )
    template = django_filters.ModelMultipleChoiceFilter(
        queryset=ConfigTemplate.objects.all(),
    )
    changed_at = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ConfigTemplateHistory
        fields = ["id", "template", "changed_by", "changed_at"]


class JackMappingFilterSet(NautobotFilterSet):
    """FilterSet for JackMapping model."""

    q = SearchFilter(
        filter_predicates={
            "comm_room": "icontains",
            "jack": "icontains",
            "description": "icontains",
        },
    )
    building = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
    )
    interface = django_filters.ModelMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = JackMapping
        fields = ["id", "building", "comm_room", "jack", "device", "interface", "is_active"]


class WorkQueueEntryFilterSet(NautobotFilterSet):
    """FilterSet for WorkQueueEntry model."""

    q = SearchFilter(
        filter_predicates={
            "comm_room": "icontains",
            "jack": "icontains",
            "status_message": "icontains",
            "requested_by": "icontains",
        },
    )
    device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
    )
    interface = django_filters.ModelMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    building = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
    )
    service = django_filters.ModelMultipleChoiceFilter(
        queryset=PortService.objects.all(),
    )
    template = django_filters.ModelMultipleChoiceFilter(
        queryset=ConfigTemplate.objects.all(),
    )
    status = django_filters.MultipleChoiceFilter(
        choices=WorkQueueEntry.StatusChoices.choices,
    )
    scheduled_time = django_filters.DateTimeFromToRangeFilter()
    attempted_time = django_filters.DateTimeFromToRangeFilter()
    completed_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = WorkQueueEntry
        fields = [
            "id",
            "device",
            "interface",
            "building",
            "service",
            "template",
            "status",
            "requested_by",
        ]


class MACAddressFilterSet(NautobotFilterSet):
    """FilterSet for MACAddress model."""

    q = SearchFilter(
        filter_predicates={
            "address": "icontains",
            "vendor": "icontains",
            "description": "icontains",
        },
    )
    mac_type = django_filters.MultipleChoiceFilter(
        choices=MACAddress.MACTypeChoices.choices,
    )
    last_device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
    )
    last_interface = django_filters.ModelMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    assigned_interface = django_filters.ModelMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    last_vlan = django_filters.NumberFilter()
    last_ip = django_filters.CharFilter(lookup_expr="icontains")
    vendor = django_filters.CharFilter(lookup_expr="icontains")
    first_seen = django_filters.DateTimeFromToRangeFilter()
    last_seen = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = MACAddress
        fields = [
            "id",
            "address",
            "mac_type",
            "vendor",
            "last_device",
            "last_interface",
            "last_vlan",
        ]


class MACAddressEntryFilterSet(NautobotFilterSet):
    """FilterSet for MACAddressEntry model."""

    q = SearchFilter(
        filter_predicates={
            "mac_address__address": "icontains",
        },
    )
    mac_address = django_filters.ModelMultipleChoiceFilter(
        queryset=MACAddress.objects.all(),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
    )
    interface = django_filters.ModelMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    vlan = django_filters.NumberFilter()
    entry_type = django_filters.MultipleChoiceFilter(
        choices=MACAddressEntry.EntryTypeChoices.choices,
    )
    collected_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = MACAddressEntry
        fields = ["id", "mac_address", "device", "interface", "vlan", "entry_type"]


class MACAddressHistoryFilterSet(NautobotFilterSet):
    """FilterSet for MACAddressHistory model."""

    q = SearchFilter(
        filter_predicates={
            "mac_address__address": "icontains",
        },
    )
    mac_address = django_filters.ModelMultipleChoiceFilter(
        queryset=MACAddress.objects.all(),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
    )
    interface = django_filters.ModelMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    vlan = django_filters.NumberFilter()
    first_seen = django_filters.DateTimeFromToRangeFilter()
    last_seen = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = MACAddressHistory
        fields = ["id", "mac_address", "device", "interface", "vlan"]


class ARPEntryFilterSet(NautobotFilterSet):
    """FilterSet for ARPEntry model."""

    q = SearchFilter(
        filter_predicates={
            "ip_address": "icontains",
            "mac_address__address": "icontains",
            "vrf": "icontains",
        },
    )
    mac_address = django_filters.ModelMultipleChoiceFilter(
        queryset=MACAddress.objects.all(),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
    )
    interface = django_filters.ModelMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    ip_address = django_filters.CharFilter(lookup_expr="icontains")
    vrf = django_filters.CharFilter(lookup_expr="icontains")
    entry_type = django_filters.MultipleChoiceFilter(
        choices=ARPEntry.EntryTypeChoices.choices,
    )
    collected_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ARPEntry
        fields = ["id", "mac_address", "device", "interface", "ip_address", "vrf", "entry_type"]


class ControlSettingFilterSet(NautobotFilterSet):
    """FilterSet for ControlSetting model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "value": "icontains",
            "description": "icontains",
        },
    )

    class Meta:
        model = ControlSetting
        fields = ["id", "name", "value"]
