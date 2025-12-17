"""URL routes for the NetAccess app UI."""

from django.urls import path
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_network_provisioning.views import (
    PortServiceUIViewSet,
    SwitchProfileUIViewSet,
    ConfigTemplateUIViewSet,
    JackMappingUIViewSet,
    WorkQueueEntryUIViewSet,
    MACAddressUIViewSet,
    MACAddressEntryUIViewSet,
    MACAddressHistoryUIViewSet,
    ARPEntryUIViewSet,
    ControlSettingUIViewSet,
    PortConfigurationRequestView,
    PortLookupAPIView,
    TemplateIDEView,
)

router = NautobotUIViewSetRouter()

# Port Configuration
router.register("port-services", PortServiceUIViewSet)
router.register("switch-profiles", SwitchProfileUIViewSet)
router.register("config-templates", ConfigTemplateUIViewSet)
router.register("jack-mappings", JackMappingUIViewSet)
router.register("work-queue", WorkQueueEntryUIViewSet)

# MAC Tracking
router.register("mac-addresses", MACAddressUIViewSet)
router.register("mac-entries", MACAddressEntryUIViewSet)
router.register("mac-history", MACAddressHistoryUIViewSet)
router.register("arp-entries", ARPEntryUIViewSet)

# System
router.register("control-settings", ControlSettingUIViewSet)

# Custom URL patterns
urlpatterns = [
    # Port Configuration Request (TWIX-style form)
    path(
        "port-config-request/",
        PortConfigurationRequestView.as_view(),
        name="port_config_request",
    ),
    # Port Lookup API
    path(
        "api/port-lookup/",
        PortLookupAPIView.as_view(),
        name="port_lookup_api",
    ),
    # Template IDE (GraphiQL-style editor)
    path(
        "template-ide/",
        TemplateIDEView.as_view(),
        name="template_ide",
    ),
    path(
        "template-ide/<uuid:pk>/",
        TemplateIDEView.as_view(),
        name="template_ide_edit",
    ),
]

# Add router URLs
urlpatterns += router.urls
