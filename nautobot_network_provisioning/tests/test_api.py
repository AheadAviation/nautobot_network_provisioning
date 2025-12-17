"""Tests for NetAccess API serializers."""

from django.test import TestCase

from nautobot_network_provisioning.models import PortService, SwitchProfile, MACAddress, ControlSetting
from nautobot_network_provisioning.api.serializers import (
    PortServiceSerializer,
    SwitchProfileSerializer,
    MACAddressSerializer,
    ControlSettingSerializer,
)


class PortServiceSerializerTest(TestCase):
    """Test cases for PortServiceSerializer."""

    def setUp(self):
        """Set up test data."""
        self.service = PortService.objects.create(
            name="Test-Service",
            description="Test description",
            is_active=True,
        )

    def test_serialize_service(self):
        """Test serializing a port service."""
        serializer = PortServiceSerializer(self.service)
        data = serializer.data
        
        self.assertEqual(data["name"], "Test-Service")
        self.assertEqual(data["description"], "Test description")
        self.assertTrue(data["is_active"])

    def test_deserialize_service(self):
        """Test deserializing port service data."""
        data = {
            "name": "New-Service",
            "description": "New description",
            "is_active": False,
        }
        serializer = PortServiceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_deserialize_invalid_service(self):
        """Test deserializing invalid port service data."""
        data = {
            "description": "Missing name",
        }
        serializer = PortServiceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)


class SwitchProfileSerializerTest(TestCase):
    """Test cases for SwitchProfileSerializer."""

    def setUp(self):
        """Set up test data."""
        self.profile = SwitchProfile.objects.create(
            name="Test Profile",
            device_type_pattern="WS-C%",
            os_version_pattern="15.%",
            priority=50,
        )

    def test_serialize_profile(self):
        """Test serializing a switch profile."""
        serializer = SwitchProfileSerializer(self.profile)
        data = serializer.data
        
        self.assertEqual(data["name"], "Test Profile")
        self.assertEqual(data["device_type_pattern"], "WS-C%")
        self.assertEqual(data["os_version_pattern"], "15.%")
        self.assertEqual(data["priority"], 50)

    def test_deserialize_profile(self):
        """Test deserializing profile data."""
        data = {
            "name": "New Profile",
            "device_type_pattern": "WS-C3850%",
            "os_version_pattern": "16.%",
            "priority": 100,
        }
        serializer = SwitchProfileSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class MACAddressSerializerTest(TestCase):
    """Test cases for MACAddressSerializer."""

    def setUp(self):
        """Set up test data."""
        self.mac = MACAddress.objects.create(
            address="AA:BB:CC:DD:EE:FF",
            mac_type=MACAddress.MACTypeChoices.ENDPOINT,
            vendor="Cisco",
        )

    def test_serialize_mac(self):
        """Test serializing a MAC address."""
        serializer = MACAddressSerializer(self.mac)
        data = serializer.data
        
        self.assertEqual(data["address"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(data["mac_type"], "endpoint")
        self.assertEqual(data["vendor"], "Cisco")

    def test_deserialize_mac(self):
        """Test deserializing MAC data."""
        data = {
            "address": "11:22:33:44:55:66",
            "mac_type": "interface",
            "vendor": "Dell",
        }
        serializer = MACAddressSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ControlSettingSerializerTest(TestCase):
    """Test cases for ControlSettingSerializer."""

    def setUp(self):
        """Set up test data."""
        self.setting = ControlSetting.objects.create(
            name="test_setting",
            value="test_value",
            description="Test description",
        )

    def test_serialize_setting(self):
        """Test serializing a control setting."""
        serializer = ControlSettingSerializer(self.setting)
        data = serializer.data
        
        self.assertEqual(data["name"], "test_setting")
        self.assertEqual(data["value"], "test_value")
        self.assertEqual(data["description"], "Test description")

    def test_deserialize_setting(self):
        """Test deserializing setting data."""
        data = {
            "name": "new_setting",
            "value": "new_value",
            "description": "New description",
        }
        serializer = ControlSettingSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
