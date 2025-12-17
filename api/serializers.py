"""REST API Serializers for the NetAccess app."""

from rest_framework import serializers
from nautobot.apps.api import NautobotModelSerializer
from nautobot.dcim.api.serializers import (
    DeviceSerializer,
    InterfaceSerializer,
    LocationSerializer,
    PlatformSerializer,
    ManufacturerSerializer,
)

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


class PortServiceSerializer(NautobotModelSerializer):
    """Serializer for PortService model."""

    class Meta:
        model = PortService
        fields = "__all__"


class SwitchProfileSerializer(NautobotModelSerializer):
    """Serializer for SwitchProfile model."""

    class Meta:
        model = SwitchProfile
        fields = "__all__"


class ConfigTemplateHistorySerializer(serializers.ModelSerializer):
    """Serializer for ConfigTemplateHistory model."""

    class Meta:
        model = ConfigTemplateHistory
        fields = [
            "id",
            "template_text",
            "changed_by",
            "changed_at",
            "change_reason",
        ]
        read_only_fields = fields


class ConfigTemplateSerializer(NautobotModelSerializer):
    """
    Serializer for ConfigTemplate model.
    
    Includes:
    - New matching fields (manufacturer, platform, software_version)
    - Date-based versioning fields
    - Nested history entries
    - Display name property
    """
    
    display_name = serializers.CharField(read_only=True)
    history = ConfigTemplateHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ConfigTemplate
        fields = [
            "id",
            "url",
            "display",
            "display_name",
            "service",
            "manufacturer",
            "platform",
            "software_version",
            "switch_profile",
            "instance",
            "version",
            "effective_date",
            "is_active",
            "superseded_by",
            "template_text",
            "created_by",
            "is_validated",
            "validation_message",
            "created",
            "last_updated",
            "tags",
            "history",
        ]
        read_only_fields = ["is_validated", "validation_message", "display_name"]


class JackMappingSerializer(NautobotModelSerializer):
    """Serializer for JackMapping model."""

    class Meta:
        model = JackMapping
        fields = "__all__"


class WorkQueueEntrySerializer(NautobotModelSerializer):
    """Serializer for WorkQueueEntry model."""

    class Meta:
        model = WorkQueueEntry
        fields = "__all__"


class MACAddressSerializer(NautobotModelSerializer):
    """Serializer for MACAddress model."""

    class Meta:
        model = MACAddress
        fields = "__all__"


class MACAddressEntrySerializer(NautobotModelSerializer):
    """Serializer for MACAddressEntry model."""

    class Meta:
        model = MACAddressEntry
        fields = "__all__"


class MACAddressHistorySerializer(NautobotModelSerializer):
    """Serializer for MACAddressHistory model."""

    class Meta:
        model = MACAddressHistory
        fields = "__all__"


class ARPEntrySerializer(NautobotModelSerializer):
    """Serializer for ARPEntry model."""

    class Meta:
        model = ARPEntry
        fields = "__all__"


class ControlSettingSerializer(NautobotModelSerializer):
    """Serializer for ControlSetting model."""

    class Meta:
        model = ControlSetting
        fields = "__all__"
