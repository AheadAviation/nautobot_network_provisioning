"""Tests for NetAccess filters."""

from django.test import TestCase

from nautobot_network_provisioning.models import PortService, SwitchProfile, MACAddress, ControlSetting
from nautobot_network_provisioning.filters import (
    PortServiceFilterSet,
    SwitchProfileFilterSet,
    MACAddressFilterSet,
    ControlSettingFilterSet,
)


class PortServiceFilterSetTest(TestCase):
    """Test cases for PortServiceFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.service1 = PortService.objects.create(
            name="Access-VoIP",
            description="Voice over IP",
            is_active=True,
        )
        self.service2 = PortService.objects.create(
            name="Access-Data",
            description="Data port",
            is_active=True,
        )
        self.service3 = PortService.objects.create(
            name="Unused-Port",
            description="Unused port configuration",
            is_active=False,
        )

    def test_filter_by_name(self):
        """Test filtering by name."""
        filterset = PortServiceFilterSet({"name": "Access-VoIP"})
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.service1)

    def test_filter_by_is_active(self):
        """Test filtering by is_active."""
        filterset = PortServiceFilterSet({"is_active": True})
        self.assertEqual(filterset.qs.count(), 2)
        
        filterset = PortServiceFilterSet({"is_active": False})
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.service3)

    def test_search_filter(self):
        """Test search filter."""
        filterset = PortServiceFilterSet({"q": "VoIP"})
        self.assertEqual(filterset.qs.count(), 1)
        
        filterset = PortServiceFilterSet({"q": "Access"})
        self.assertEqual(filterset.qs.count(), 2)
        
        filterset = PortServiceFilterSet({"q": "port"})
        self.assertEqual(filterset.qs.count(), 2)  # Matches description


class SwitchProfileFilterSetTest(TestCase):
    """Test cases for SwitchProfileFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.profile1 = SwitchProfile.objects.create(
            name="Catalyst 3850",
            device_type_pattern="WS-C3850%",
            os_version_pattern="16.%",
            priority=10,
        )
        self.profile2 = SwitchProfile.objects.create(
            name="Catalyst 2960",
            device_type_pattern="WS-C2960%",
            os_version_pattern="15.%",
            priority=20,
        )

    def test_filter_by_name(self):
        """Test filtering by name."""
        filterset = SwitchProfileFilterSet({"name": "Catalyst 3850"})
        self.assertEqual(filterset.qs.count(), 1)

    def test_search_filter(self):
        """Test search filter."""
        filterset = SwitchProfileFilterSet({"q": "3850"})
        self.assertEqual(filterset.qs.count(), 1)
        
        filterset = SwitchProfileFilterSet({"q": "Catalyst"})
        self.assertEqual(filterset.qs.count(), 2)


class MACAddressFilterSetTest(TestCase):
    """Test cases for MACAddressFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.mac1 = MACAddress.objects.create(
            address="AA:BB:CC:DD:EE:FF",
            mac_type=MACAddress.MACTypeChoices.ENDPOINT,
            vendor="Cisco",
        )
        self.mac2 = MACAddress.objects.create(
            address="11:22:33:44:55:66",
            mac_type=MACAddress.MACTypeChoices.INTERFACE,
            vendor="Dell",
        )
        self.mac3 = MACAddress.objects.create(
            address="AA:AA:AA:AA:AA:AA",
            mac_type=MACAddress.MACTypeChoices.VIRTUAL,
            vendor="VMware",
        )

    def test_filter_by_mac_type(self):
        """Test filtering by MAC type."""
        filterset = MACAddressFilterSet({"mac_type": ["endpoint"]})
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.mac1)

    def test_filter_by_vendor(self):
        """Test filtering by vendor."""
        filterset = MACAddressFilterSet({"vendor": "Cisco"})
        self.assertEqual(filterset.qs.count(), 1)

    def test_search_filter(self):
        """Test search filter."""
        filterset = MACAddressFilterSet({"q": "AA:BB"})
        self.assertEqual(filterset.qs.count(), 1)
        
        filterset = MACAddressFilterSet({"q": "VMware"})
        self.assertEqual(filterset.qs.count(), 1)


class ControlSettingFilterSetTest(TestCase):
    """Test cases for ControlSettingFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.setting1 = ControlSetting.objects.create(
            name="queue_processing_enabled",
            value="true",
            description="Enable queue processing",
        )
        self.setting2 = ControlSetting.objects.create(
            name="write_mem_enabled",
            value="false",
            description="Save config after changes",
        )

    def test_filter_by_name(self):
        """Test filtering by name."""
        filterset = ControlSettingFilterSet({"name": "queue_processing_enabled"})
        self.assertEqual(filterset.qs.count(), 1)

    def test_filter_by_value(self):
        """Test filtering by value."""
        filterset = ControlSettingFilterSet({"value": "true"})
        self.assertEqual(filterset.qs.count(), 1)

    def test_search_filter(self):
        """Test search filter."""
        filterset = ControlSettingFilterSet({"q": "queue"})
        self.assertEqual(filterset.qs.count(), 1)
        
        filterset = ControlSettingFilterSet({"q": "enabled"})
        self.assertEqual(filterset.qs.count(), 2)
