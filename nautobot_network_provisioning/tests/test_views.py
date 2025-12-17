"""Tests for NetAccess views - basic import and structure tests."""

from django.test import TestCase

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
)
from nautobot_network_provisioning.models import PortService, SwitchProfile, MACAddress, ControlSetting
from nautobot_network_provisioning.tables import (
    PortServiceTable,
    SwitchProfileTable,
    MACAddressTable,
    ControlSettingTable,
)
from nautobot_network_provisioning.filters import (
    PortServiceFilterSet,
    SwitchProfileFilterSet,
    MACAddressFilterSet,
    ControlSettingFilterSet,
)


class ViewSetConfigurationTest(TestCase):
    """Test that ViewSets are properly configured."""

    def test_service_viewset_configuration(self):
        """Test PortServiceUIViewSet configuration."""
        viewset = PortServiceUIViewSet
        
        self.assertEqual(viewset.queryset.model, PortService)
        self.assertEqual(viewset.table_class, PortServiceTable)
        self.assertEqual(viewset.filterset_class, PortServiceFilterSet)

    def test_switch_profile_viewset_configuration(self):
        """Test SwitchProfileUIViewSet configuration."""
        viewset = SwitchProfileUIViewSet
        
        self.assertEqual(viewset.queryset.model, SwitchProfile)
        self.assertEqual(viewset.table_class, SwitchProfileTable)
        self.assertEqual(viewset.filterset_class, SwitchProfileFilterSet)

    def test_mac_address_viewset_configuration(self):
        """Test MACAddressUIViewSet configuration."""
        viewset = MACAddressUIViewSet
        
        self.assertEqual(viewset.queryset.model, MACAddress)
        self.assertEqual(viewset.table_class, MACAddressTable)
        self.assertEqual(viewset.filterset_class, MACAddressFilterSet)

    def test_control_setting_viewset_configuration(self):
        """Test ControlSettingUIViewSet configuration."""
        viewset = ControlSettingUIViewSet
        
        self.assertEqual(viewset.queryset.model, ControlSetting)
        self.assertEqual(viewset.table_class, ControlSettingTable)
        self.assertEqual(viewset.filterset_class, ControlSettingFilterSet)

    def test_read_only_viewsets_have_limited_actions(self):
        """Test that read-only viewsets have appropriate action buttons."""
        # MACAddressEntry, MACAddressHistory, ARPEntry are typically read-only
        self.assertEqual(MACAddressEntryUIViewSet.action_buttons, ("export",))
        self.assertEqual(MACAddressHistoryUIViewSet.action_buttons, ("export",))
        self.assertEqual(ARPEntryUIViewSet.action_buttons, ("export",))


class ViewSetImportsTest(TestCase):
    """Test that all ViewSets can be imported."""

    def test_all_viewsets_importable(self):
        """Test that all ViewSets are importable."""
        viewsets = [
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
        ]
        
        for viewset in viewsets:
            self.assertIsNotNone(viewset)
            self.assertTrue(hasattr(viewset, 'queryset'))
