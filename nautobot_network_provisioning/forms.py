"""Forms for the NetAccess app."""

from django import forms
from nautobot.apps.forms import (
    NautobotModelForm,
    NautobotBulkEditForm,
    NautobotFilterForm,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
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
from nautobot_network_provisioning.widgets import Jinja2EditorWidget


# =============================================================================
# Automated Task Forms (formerly Port Service)
# =============================================================================

class PortServiceForm(NautobotModelForm):
    """Form for creating/editing Automated Task instances."""

    class Meta:
        model = PortService
        fields = ["name", "description", "is_active", "tags"]
        labels = {
            "name": "Task Name",
            "description": "Task Description",
            "is_active": "Active",
        }
        help_texts = {
            "name": "Unique name for this automated task (e.g., 'Enable VoIP Port', 'Set Access VLAN')",
            "description": "Description of what this automated task does",
            "is_active": "Whether this task is available for selection",
        }


class PortServiceBulkEditForm(NautobotBulkEditForm):
    """Bulk edit form for Automated Task instances."""

    pk = forms.ModelMultipleChoiceField(
        queryset=PortService.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    is_active = forms.NullBooleanField(required=False)

    class Meta:
        model = PortService
        nullable_fields = ["description"]


class PortServiceFilterForm(NautobotFilterForm):
    """Filter form for Automated Task list view."""

    model = PortService
    q = forms.CharField(required=False, label="Search")
    is_active = forms.NullBooleanField(required=False, label="Active")
    tags = TagFilterField(model)


# Backward compatibility aliases
AutomatedTaskForm = PortServiceForm
AutomatedTaskBulkEditForm = PortServiceBulkEditForm
AutomatedTaskFilterForm = PortServiceFilterForm


# =============================================================================
# SwitchProfile Forms
# =============================================================================

class SwitchProfileForm(NautobotModelForm):
    """Form for creating/editing SwitchProfile instances."""

    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
    )

    class Meta:
        model = SwitchProfile
        fields = [
            "name",
            "device_type_pattern",
            "os_version_pattern",
            "platform",
            "priority",
            "tags",
        ]


class SwitchProfileBulkEditForm(NautobotBulkEditForm):
    """Bulk edit form for SwitchProfile instances."""

    pk = forms.ModelMultipleChoiceField(
        queryset=SwitchProfile.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
    )
    priority = forms.IntegerField(required=False)

    class Meta:
        model = SwitchProfile
        nullable_fields = ["platform"]


class SwitchProfileFilterForm(NautobotFilterForm):
    """Filter form for SwitchProfile list view."""

    model = SwitchProfile
    q = forms.CharField(required=False, label="Search")
    platform = DynamicModelMultipleChoiceField(
        queryset=Platform.objects.all(),
        required=False,
    )
    tags = TagFilterField(model)


# =============================================================================
# ConfigTemplate Forms
# =============================================================================

class ConfigTemplateForm(NautobotModelForm):
    """
    Form for creating/editing ConfigTemplate instances.
    
    Templates are matched using DCIM Software Versions which cascade:
    - Software Versions → Platform → Manufacturer
    
    Includes:
    - Automated Task selection
    - DCIM-based matching (manufacturer/platform/software_versions)
    - Jinja2 IDE editor widget with syntax highlighting
    - Live preview and validation
    """

    service = DynamicModelChoiceField(
        queryset=PortService.objects.all(),
        label="Automated Task",
        help_text="The automated task this template belongs to",
    )
    
    # DCIM matching fields
    manufacturer = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=True,
        help_text="Device manufacturer (e.g., Cisco, Dell, Arista)",
    )
    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=True,
        query_params={"manufacturer_id": "$manufacturer"},
        help_text="Platform/OS type (e.g., cisco_ios, dell_sonic)",
    )
    # ManyToMany - select multiple software versions
    software_versions = DynamicModelMultipleChoiceField(
        queryset=SoftwareVersion.objects.all(),
        required=False,
        query_params={"platform_id": "$platform"},
        help_text="Select software versions this template applies to (leave empty for ALL versions of this platform)",
    )

    class Meta:
        model = ConfigTemplate
        fields = [
            "service",
            "manufacturer",
            "platform",
            "software_versions",
            "effective_date",
            "is_active",
            "version",
            "template_text",
            "created_by",
            "tags",
        ]
        widgets = {
            "template_text": Jinja2EditorWidget(),
            "effective_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
            }),
        }
        help_texts = {
            "template_text": (
                "Jinja2 template syntax. Use the variable helper panel on the right "
                "to insert available variables. Press Ctrl+Enter for live preview."
            ),
            "effective_date": "Date when this template version becomes active",
            "is_active": "Whether this template is available for use",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up fieldsets for better organization in the UI
        self.fieldsets = [
            ("Task & Device Matching", ["service", "manufacturer", "platform", "software_versions"]),
            ("Versioning", ["effective_date", "is_active", "version"]),
            ("Template", ["template_text"]),
            ("Metadata", ["created_by", "tags"]),
        ]
    
    def clean_template_text(self):
        """
        Validate the Jinja2 template syntax.
        
        Returns detailed error messages with line numbers if invalid.
        """
        template_text = self.cleaned_data.get("template_text", "")
        
        if not template_text:
            return template_text
        
        # Import the validator
        from nautobot_network_provisioning.validators import (
            validate_jinja2_syntax,
            format_validation_error_for_form,
        )
        
        result = validate_jinja2_syntax(template_text)
        
        if not result.is_valid:
            error_message = format_validation_error_for_form(result)
            raise forms.ValidationError(
                f"Jinja2 Template Validation Failed:\n\n{error_message}",
                code="invalid_jinja2",
            )
        
        # Add warnings as form warnings (if supported)
        if result.warnings:
            # Store warnings for display
            if not hasattr(self, "_template_warnings"):
                self._template_warnings = []
            self._template_warnings.extend(result.warnings)
        
        return template_text
    
    def get_template_warnings(self):
        """Get any template warnings from validation."""
        return getattr(self, "_template_warnings", [])


class ConfigTemplateBulkEditForm(NautobotBulkEditForm):
    """Bulk edit form for ConfigTemplate instances."""

    pk = forms.ModelMultipleChoiceField(
        queryset=ConfigTemplate.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    manufacturer = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
    )
    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
    )
    is_active = forms.NullBooleanField(required=False)

    class Meta:
        model = ConfigTemplate
        nullable_fields = []


class ConfigTemplateFilterForm(NautobotFilterForm):
    """Filter form for ConfigTemplate list view."""

    model = ConfigTemplate
    q = forms.CharField(required=False, label="Search")
    service = DynamicModelMultipleChoiceField(
        queryset=PortService.objects.all(),
        required=False,
        label="Automated Task",
    )
    manufacturer = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
    )
    platform = DynamicModelMultipleChoiceField(
        queryset=Platform.objects.all(),
        required=False,
    )
    software_versions = DynamicModelMultipleChoiceField(
        queryset=SoftwareVersion.objects.all(),
        required=False,
        label="Software Versions",
    )
    is_active = forms.NullBooleanField(required=False, label="Active")
    tags = TagFilterField(model)


# =============================================================================
# JackMapping Forms
# =============================================================================

class JackMappingForm(NautobotModelForm):
    """Form for creating/editing JackMapping instances."""

    building = DynamicModelChoiceField(
        queryset=Location.objects.all(),
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
    )
    interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        query_params={"device_id": "$device"},
    )

    class Meta:
        model = JackMapping
        fields = [
            "building",
            "comm_room",
            "jack",
            "device",
            "interface",
            "description",
            "is_active",
            "tags",
        ]


class JackMappingBulkEditForm(NautobotBulkEditForm):
    """Bulk edit form for JackMapping instances."""

    pk = forms.ModelMultipleChoiceField(
        queryset=JackMapping.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    is_active = forms.NullBooleanField(required=False)

    class Meta:
        model = JackMapping
        nullable_fields = ["description"]


class JackMappingFilterForm(NautobotFilterForm):
    """Filter form for JackMapping list view."""

    model = JackMapping
    q = forms.CharField(required=False, label="Search")
    building = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
    )
    device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )
    is_active = forms.NullBooleanField(required=False)
    tags = TagFilterField(model)


# =============================================================================
# WorkQueueEntry Forms
# =============================================================================

class WorkQueueEntryForm(NautobotModelForm):
    """Form for creating/editing WorkQueueEntry instances."""

    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
    )
    interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        query_params={"device_id": "$device"},
    )
    building = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
    )
    service = DynamicModelChoiceField(
        queryset=PortService.objects.all(),
    )
    template = DynamicModelChoiceField(
        queryset=ConfigTemplate.objects.all(),
        query_params={"service_id": "$service"},
    )

    class Meta:
        model = WorkQueueEntry
        fields = [
            "device",
            "interface",
            "building",
            "comm_room",
            "jack",
            "service",
            "template",
            "vlan",
            "scheduled_time",
            "status",
            "status_message",
            "requested_by",
            "request_ip",
            "tags",
        ]


class WorkQueueEntryBulkEditForm(NautobotBulkEditForm):
    """Bulk edit form for WorkQueueEntry instances."""

    pk = forms.ModelMultipleChoiceField(
        queryset=WorkQueueEntry.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    status = forms.ChoiceField(
        choices=WorkQueueEntry.StatusChoices.choices,
        required=False,
    )

    class Meta:
        model = WorkQueueEntry
        nullable_fields = ["status_message", "vlan"]


class WorkQueueEntryFilterForm(NautobotFilterForm):
    """Filter form for WorkQueueEntry list view."""

    model = WorkQueueEntry
    q = forms.CharField(required=False, label="Search")
    device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )
    service = DynamicModelMultipleChoiceField(
        queryset=PortService.objects.all(),
        required=False,
    )
    status = forms.MultipleChoiceField(
        choices=WorkQueueEntry.StatusChoices.choices,
        required=False,
    )
    tags = TagFilterField(model)


# =============================================================================
# MACAddress Forms
# =============================================================================

class MACAddressForm(NautobotModelForm):
    """Form for creating/editing MACAddress instances."""

    assigned_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
    )
    last_device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )
    last_interface = DynamicModelChoiceField(
        queryset=Interface.objects.all(),
        required=False,
    )

    class Meta:
        model = MACAddress
        fields = [
            "address",
            "mac_type",
            "vendor",
            "description",
            "assigned_interface",
            "last_device",
            "last_interface",
            "last_vlan",
            "last_ip",
            "tags",
        ]


class MACAddressFilterForm(NautobotFilterForm):
    """Filter form for MACAddress list view."""

    model = MACAddress
    q = forms.CharField(required=False, label="Search")
    mac_type = forms.MultipleChoiceField(
        choices=MACAddress.MACTypeChoices.choices,
        required=False,
    )
    last_device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )
    vendor = forms.CharField(required=False)
    tags = TagFilterField(model)


# =============================================================================
# MACAddressEntry Forms
# =============================================================================

class MACAddressEntryFilterForm(NautobotFilterForm):
    """Filter form for MACAddressEntry list view."""

    model = MACAddressEntry
    q = forms.CharField(required=False, label="Search")
    device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )
    interface = DynamicModelMultipleChoiceField(
        queryset=Interface.objects.all(),
        required=False,
    )
    vlan = forms.IntegerField(required=False)
    entry_type = forms.MultipleChoiceField(
        choices=MACAddressEntry.EntryTypeChoices.choices,
        required=False,
    )


# =============================================================================
# MACAddressHistory Forms
# =============================================================================

class MACAddressHistoryFilterForm(NautobotFilterForm):
    """Filter form for MACAddressHistory list view."""

    model = MACAddressHistory
    q = forms.CharField(required=False, label="Search")
    device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )
    interface = DynamicModelMultipleChoiceField(
        queryset=Interface.objects.all(),
        required=False,
    )
    vlan = forms.IntegerField(required=False)


# =============================================================================
# ARPEntry Forms
# =============================================================================

class ARPEntryFilterForm(NautobotFilterForm):
    """Filter form for ARPEntry list view."""

    model = ARPEntry
    q = forms.CharField(required=False, label="Search")
    device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
    )
    ip_address = forms.CharField(required=False)
    vrf = forms.CharField(required=False)
    entry_type = forms.MultipleChoiceField(
        choices=ARPEntry.EntryTypeChoices.choices,
        required=False,
    )


# =============================================================================
# ControlSetting Forms
# =============================================================================

class ControlSettingForm(NautobotModelForm):
    """Form for creating/editing ControlSetting instances."""

    class Meta:
        model = ControlSetting
        fields = ["name", "value", "description"]


class ControlSettingFilterForm(NautobotFilterForm):
    """Filter form for ControlSetting list view."""

    model = ControlSetting
    q = forms.CharField(required=False, label="Search")


# =============================================================================
# Port Configuration Request Form (TWIX-style)
# =============================================================================

class PortConfigurationRequestForm(forms.Form):
    """
    TWIX-style port configuration request form.
    
    Allows user to specify Building/Room/Jack and Service to schedule
    a port configuration change.
    """
    
    building = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=True,
        help_text="Select the building location",
    )
    comm_room = forms.CharField(
        max_length=50,
        required=True,
        label="Communications Room",
        help_text="Enter the communications room identifier (e.g., '040', 'MDF-1')",
    )
    jack = forms.CharField(
        max_length=50,
        required=True,
        label="Jack",
        help_text="Enter the jack identifier (e.g., '0228', 'A-101')",
    )
    service = DynamicModelChoiceField(
        queryset=PortService.objects.filter(is_active=True),
        required=True,
        label="Service/Template",
        help_text="Select the port configuration service to apply",
    )
    scheduled_time = forms.DateTimeField(
        required=True,
        label="Schedule Time",
        help_text="When should this change be applied?",
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
            }
        ),
    )
    vlan = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=4094,
        label="VLAN (optional)",
        help_text="Optional VLAN override (1-4094)",
    )
    
    def clean_scheduled_time(self):
        """Ensure scheduled time is in the future."""
        from django.utils import timezone
        scheduled = self.cleaned_data.get("scheduled_time")
        if scheduled and scheduled < timezone.now():
            # Allow scheduling up to 5 minutes in the past (for immediate execution)
            from datetime import timedelta
            if scheduled < timezone.now() - timedelta(minutes=5):
                raise forms.ValidationError("Scheduled time must be in the future")
        return scheduled
