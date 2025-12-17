"""Views for the NetAccess app."""

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from nautobot.apps.views import NautobotUIViewSet

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
from nautobot_network_provisioning.forms import (
    PortServiceForm,
    PortServiceBulkEditForm,
    PortServiceFilterForm,
    SwitchProfileForm,
    SwitchProfileBulkEditForm,
    SwitchProfileFilterForm,
    ConfigTemplateForm,
    ConfigTemplateBulkEditForm,
    ConfigTemplateFilterForm,
    JackMappingForm,
    JackMappingBulkEditForm,
    JackMappingFilterForm,
    WorkQueueEntryForm,
    WorkQueueEntryBulkEditForm,
    WorkQueueEntryFilterForm,
    MACAddressForm,
    MACAddressFilterForm,
    MACAddressEntryFilterForm,
    MACAddressHistoryFilterForm,
    ARPEntryFilterForm,
    ControlSettingForm,
    ControlSettingFilterForm,
    PortConfigurationRequestForm,
)
from nautobot_network_provisioning.filters import (
    PortServiceFilterSet,
    SwitchProfileFilterSet,
    ConfigTemplateFilterSet,
    JackMappingFilterSet,
    WorkQueueEntryFilterSet,
    MACAddressFilterSet,
    MACAddressEntryFilterSet,
    MACAddressHistoryFilterSet,
    ARPEntryFilterSet,
    ControlSettingFilterSet,
)
from nautobot_network_provisioning.tables import (
    PortServiceTable,
    SwitchProfileTable,
    ConfigTemplateTable,
    JackMappingTable,
    WorkQueueEntryTable,
    MACAddressTable,
    MACAddressEntryTable,
    MACAddressHistoryTable,
    ARPEntryTable,
    ControlSettingTable,
)
from nautobot_network_provisioning.api.serializers import (
    PortServiceSerializer,
    SwitchProfileSerializer,
    ConfigTemplateSerializer,
    JackMappingSerializer,
    WorkQueueEntrySerializer,
    MACAddressSerializer,
    MACAddressEntrySerializer,
    MACAddressHistorySerializer,
    ARPEntrySerializer,
    ControlSettingSerializer,
)


class PortServiceUIViewSet(NautobotUIViewSet):
    """
    UI ViewSet for PortService (Automated Task) model.
    
    Includes custom detail view showing all associated templates.
    """

    queryset = PortService.objects.prefetch_related(
        "templates",
        "templates__manufacturer",
        "templates__platform", 
        "templates__software_version",
    )
    table_class = PortServiceTable
    form_class = PortServiceForm
    filterset_class = PortServiceFilterSet
    filterset_form_class = PortServiceFilterForm
    bulk_update_form_class = PortServiceBulkEditForm
    serializer_class = PortServiceSerializer
    lookup_field = "pk"
    
    def get_extra_context(self, request, instance=None):
        """Add templates to the context for detail view."""
        context = super().get_extra_context(request, instance)
        if instance:
            # Get all templates for this task, ordered by platform and version
            context["templates"] = instance.templates.select_related(
                "manufacturer",
                "platform",
                "software_version",
            ).order_by("platform__name", "software_version__version")
        return context


class SwitchProfileUIViewSet(NautobotUIViewSet):
    """UI ViewSet for SwitchProfile model."""

    queryset = SwitchProfile.objects.all()
    table_class = SwitchProfileTable
    form_class = SwitchProfileForm
    filterset_class = SwitchProfileFilterSet
    filterset_form_class = SwitchProfileFilterForm
    bulk_update_form_class = SwitchProfileBulkEditForm
    serializer_class = SwitchProfileSerializer
    lookup_field = "pk"


class ConfigTemplateUIViewSet(NautobotUIViewSet):
    """
    UI ViewSet for ConfigTemplate model.
    
    Includes custom detail view template with syntax highlighting
    and version history display.
    """

    queryset = ConfigTemplate.objects.select_related(
        'service', 'manufacturer', 'platform', 'software_version', 'switch_profile'
    ).prefetch_related('history')
    table_class = ConfigTemplateTable
    form_class = ConfigTemplateForm
    filterset_class = ConfigTemplateFilterSet
    filterset_form_class = ConfigTemplateFilterForm
    bulk_update_form_class = ConfigTemplateBulkEditForm
    serializer_class = ConfigTemplateSerializer
    lookup_field = "pk"


class JackMappingUIViewSet(NautobotUIViewSet):
    """UI ViewSet for JackMapping model."""

    queryset = JackMapping.objects.all()
    table_class = JackMappingTable
    form_class = JackMappingForm
    filterset_class = JackMappingFilterSet
    filterset_form_class = JackMappingFilterForm
    bulk_update_form_class = JackMappingBulkEditForm
    serializer_class = JackMappingSerializer
    lookup_field = "pk"


class WorkQueueEntryUIViewSet(NautobotUIViewSet):
    """UI ViewSet for WorkQueueEntry model."""

    queryset = WorkQueueEntry.objects.all()
    table_class = WorkQueueEntryTable
    form_class = WorkQueueEntryForm
    filterset_class = WorkQueueEntryFilterSet
    filterset_form_class = WorkQueueEntryFilterForm
    bulk_update_form_class = WorkQueueEntryBulkEditForm
    serializer_class = WorkQueueEntrySerializer
    lookup_field = "pk"


class MACAddressUIViewSet(NautobotUIViewSet):
    """UI ViewSet for MACAddress model."""

    queryset = MACAddress.objects.all()
    table_class = MACAddressTable
    form_class = MACAddressForm
    filterset_class = MACAddressFilterSet
    filterset_form_class = MACAddressFilterForm
    serializer_class = MACAddressSerializer
    lookup_field = "pk"


class MACAddressEntryUIViewSet(NautobotUIViewSet):
    """UI ViewSet for MACAddressEntry model."""

    queryset = MACAddressEntry.objects.all()
    table_class = MACAddressEntryTable
    filterset_class = MACAddressEntryFilterSet
    filterset_form_class = MACAddressEntryFilterForm
    serializer_class = MACAddressEntrySerializer
    lookup_field = "pk"
    # MACAddressEntry is typically read-only (populated by jobs)
    action_buttons = ("export",)


class MACAddressHistoryUIViewSet(NautobotUIViewSet):
    """UI ViewSet for MACAddressHistory model."""

    queryset = MACAddressHistory.objects.all()
    table_class = MACAddressHistoryTable
    filterset_class = MACAddressHistoryFilterSet
    filterset_form_class = MACAddressHistoryFilterForm
    serializer_class = MACAddressHistorySerializer
    lookup_field = "pk"
    # MACAddressHistory is read-only (populated by jobs)
    action_buttons = ("export",)


class ARPEntryUIViewSet(NautobotUIViewSet):
    """UI ViewSet for ARPEntry model."""

    queryset = ARPEntry.objects.all()
    table_class = ARPEntryTable
    filterset_class = ARPEntryFilterSet
    filterset_form_class = ARPEntryFilterForm
    serializer_class = ARPEntrySerializer
    lookup_field = "pk"
    # ARPEntry is typically read-only (populated by jobs)
    action_buttons = ("export",)


class ControlSettingUIViewSet(NautobotUIViewSet):
    """UI ViewSet for ControlSetting model."""

    queryset = ControlSetting.objects.all()
    table_class = ControlSettingTable
    form_class = ControlSettingForm
    filterset_class = ControlSettingFilterSet
    filterset_form_class = ControlSettingFilterForm
    serializer_class = ControlSettingSerializer
    lookup_field = "pk"


# =============================================================================
# Port Configuration Request View (TWIX-style)
# =============================================================================

class PortConfigurationRequestView(View):
    """
    TWIX-style port configuration request view.
    
    Allows users to submit port configuration requests by specifying:
    - Building
    - Communications Room  
    - Jack
    - Service/Template
    - Scheduled Time
    
    The view will:
    1. Look up the Device and Interface from Building/Room/Jack
    2. Find the appropriate template for the device
    3. Create a WorkQueueEntry for scheduled execution
    """
    
    template_name = "nautobot_network_provisioning/port_config_request.html"
    
    def get(self, request):
        """Display the port configuration request form."""
        form = PortConfigurationRequestForm()
        
        # Get some stats for the page
        pending_count = WorkQueueEntry.objects.filter(status="pending").count()
        failed_count = WorkQueueEntry.objects.filter(status="failed").count()
        
        context = {
            "form": form,
            "pending_count": pending_count,
            "failed_count": failed_count,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Process the port configuration request form."""
        form = PortConfigurationRequestForm(request.POST)
        
        if form.is_valid():
            building = form.cleaned_data["building"]
            comm_room = form.cleaned_data["comm_room"]
            jack = form.cleaned_data["jack"]
            service = form.cleaned_data["service"]
            scheduled_time = form.cleaned_data["scheduled_time"]
            vlan = form.cleaned_data.get("vlan")
            
            # Look up the device and interface
            from nautobot_network_provisioning.services.jack_lookup import find_interface_unified
            
            results = find_interface_unified(
                building_name=building.name,
                comm_room=comm_room,
                jack=jack,
            )
            
            if not results:
                messages.error(
                    request,
                    f"No port found for {building.name}/{comm_room}/{jack}. "
                    "Please verify the building, communications room, and jack."
                )
                context = {"form": form}
                return render(request, self.template_name, context)
            
            if len(results) > 1:
                messages.warning(
                    request,
                    f"Multiple ports found ({len(results)}). Using the first match."
                )
            
            result = results[0]
            device = result.device
            interface = result.interface
            
            # Find the appropriate template for this device and service
            from nautobot_network_provisioning.services.template_matcher import find_template_for_device
            
            template = find_template_for_device(device, service)
            
            if not template:
                # Try to get any template for the service
                template = ConfigTemplate.objects.filter(
                    service=service
                ).order_by("-version").first()
            
            if not template:
                messages.error(
                    request,
                    f"No configuration template found for service '{service.name}' "
                    f"that matches device {device.name}."
                )
                context = {"form": form}
                return render(request, self.template_name, context)
            
            # Get the username
            requested_by = request.user.username if request.user.is_authenticated else "anonymous"
            request_ip = self._get_client_ip(request)
            
            # Create the WorkQueueEntry
            entry = WorkQueueEntry.objects.create(
                device=device,
                interface=interface,
                building=building,
                comm_room=comm_room,
                jack=jack,
                service=service,
                template=template,
                vlan=vlan,
                scheduled_time=scheduled_time,
                status="pending",
                requested_by=requested_by,
                request_ip=request_ip,
            )
            
            messages.success(
                request,
                f"Port configuration scheduled successfully! "
                f"Device: {device.name}, Interface: {interface.name}, "
                f"Service: {service.name}. "
                f"Scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M')}"
            )
            
            # Redirect to the work queue list
            return redirect("plugins:nautobot_network_provisioning:workqueueentry_list")
        
        # Form is not valid
        context = {"form": form}
        return render(request, self.template_name, context)
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class PortLookupAPIView(View):
    """API view for looking up ports by Building/Room/Jack."""
    
    def get(self, request):
        """Look up a port and return JSON."""
        building_name = request.GET.get("building", "")
        comm_room = request.GET.get("comm_room", "")
        jack = request.GET.get("jack", "")
        
        if not building_name:
            return JsonResponse({"error": "Building name is required"}, status=400)
        
        from nautobot_network_provisioning.services.jack_lookup import find_interface_unified
        
        results = find_interface_unified(
            building_name=building_name,
            comm_room=comm_room,
            jack=jack,
        )
        
        return JsonResponse({
            "count": len(results),
            "results": [r.to_dict() for r in results],
        })


class TemplateIDEView(View):
    """
    GraphiQL-style IDE for editing Jinja2 templates.
    
    Provides a full-page editing experience with:
    - Syntax-highlighted editor (CodeMirror)
    - Live preview/render output
    - Context variable input (JSON or GraphQL)
    - Keyboard shortcuts
    - Save functionality
    """
    
    template_name = "nautobot_network_provisioning/template_ide.html"
    
    def get(self, request, pk=None):
        """Display the template IDE."""
        from nautobot.dcim.models import Manufacturer, Platform
        
        template = None
        default_template = """! Example Cisco IOS interface configuration
interface {{ interface }}
  description {{ description | default('Configured by NetAccess') }}
  switchport mode access
  switchport access vlan {{ vlan | default(100) }}
{% if voice_vlan %}
  switchport voice vlan {{ voice_vlan }}
{% endif %}
  spanning-tree portfast
  no shutdown
"""
        default_context = """{
  "interface": "GigabitEthernet1/0/1",
  "description": "User workstation",
  "vlan": 100,
  "voice_vlan": 200
}"""
        
        # Default GraphQL query to fetch device data
        default_graphql = """{
  device(id: $deviceId) {
    name
    primary_ip4 {
      address
    }
    device_type {
      manufacturer {
        name
      }
      model
    }
    platform {
      name
    }
    interfaces {
      name
      description
      enabled
      untagged_vlan {
        vid
        name
      }
    }
  }
}"""
        
        if pk:
            template = ConfigTemplate.objects.filter(pk=pk).select_related(
                "service", "manufacturer", "platform"
            ).first()
            if template:
                default_template = template.template_text or default_template
        
        context = {
            "template": template,
            "default_template": default_template,
            "default_context": default_context,
            "default_graphql": default_graphql,
            "preview_url": "/api/plugins/network-provisioning/template-preview/",
            # For save modal
            "automated_tasks": PortService.objects.filter(is_active=True),
            "manufacturers": Manufacturer.objects.all(),
            "platforms": Platform.objects.all(),
        }
        
        return render(request, self.template_name, context)
