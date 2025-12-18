"""Phase 3: Portal URLs."""

from django.urls import path

from nautobot_network_provisioning.portal_views import PortalRequestFormView, PortalView

urlpatterns = [
    path("portal/", PortalView.as_view(), name="portal"),
    path("portal/<slug:slug>/", PortalRequestFormView.as_view(), name="portal_request_form"),
]


