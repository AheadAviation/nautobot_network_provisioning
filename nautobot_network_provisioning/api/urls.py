"""API URL routes for the NetAccess app."""

from django.urls import path
from nautobot.apps.api import OrderedDefaultRouter

from nautobot_network_provisioning.api.views import (
    PortServiceViewSet,
    SwitchProfileViewSet,
    ConfigTemplateViewSet,
    JackMappingViewSet,
    WorkQueueEntryViewSet,
    MACAddressViewSet,
    MACAddressEntryViewSet,
    MACAddressHistoryViewSet,
    ARPEntryViewSet,
    ControlSettingViewSet,
    # Template API endpoints
    template_preview,
    template_validate,
    template_variables,
)

router = OrderedDefaultRouter()

# Port Configuration
router.register("port-services", PortServiceViewSet)
router.register("switch-profiles", SwitchProfileViewSet)
router.register("config-templates", ConfigTemplateViewSet)
router.register("jack-mappings", JackMappingViewSet)
router.register("work-queue", WorkQueueEntryViewSet)

# MAC Tracking
router.register("mac-addresses", MACAddressViewSet)
router.register("mac-entries", MACAddressEntryViewSet)
router.register("mac-history", MACAddressHistoryViewSet)
router.register("arp-entries", ARPEntryViewSet)

# System
router.register("control-settings", ControlSettingViewSet)

# Additional URL patterns for non-viewset endpoints
urlpatterns = [
    # Template preview and validation API
    path("template-preview/", template_preview, name="template-preview"),
    path("template-validate/", template_validate, name="template-validate"),
    path("template-variables/", template_variables, name="template-variables"),
]

# Add router URLs
urlpatterns += router.urls
