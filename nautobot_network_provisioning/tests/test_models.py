"""Tests for NetAccess models."""

from django.test import TestCase
from django.db import IntegrityError
from datetime import datetime, timezone, timedelta

from nautobot_network_provisioning.models import (
    PortService,
    SwitchProfile,
    ConfigTemplate,
    MACAddress,
    ControlSetting,
)


class PortServiceModelTest(TestCase):
    """Test cases for the PortService model."""

    def test_create_service(self):
        """Test creating a PortService."""
        service = PortService.objects.create(
            name="Access-VoIP",
            description="Voice over IP port configuration",
            is_active=True,
        )
        self.assertEqual(str(service), "Access-VoIP")
        self.assertTrue(service.is_active)
        self.assertEqual(service.description, "Voice over IP port configuration")

    def test_service_unique_name(self):
        """Test that service names must be unique."""
        PortService.objects.create(name="Test-Service")
        with self.assertRaises(IntegrityError):
            PortService.objects.create(name="Test-Service")

    def test_service_default_is_active(self):
        """Test that is_active defaults to True."""
        service = PortService.objects.create(name="Default-Active-Service")
        self.assertTrue(service.is_active)

    def test_service_ordering(self):
        """Test services are ordered by name."""
        PortService.objects.create(name="Zebra-Service")
        PortService.objects.create(name="Alpha-Service")
        PortService.objects.create(name="Middle-Service")
        
        services = list(PortService.objects.all())
        self.assertEqual(services[0].name, "Alpha-Service")
        self.assertEqual(services[1].name, "Middle-Service")
        self.assertEqual(services[2].name, "Zebra-Service")


class SwitchProfileModelTest(TestCase):
    """Test cases for the SwitchProfile model."""

    def test_create_switch_profile(self):
        """Test creating a SwitchProfile."""
        profile = SwitchProfile.objects.create(
            name="Catalyst 3850 IOS-XE 16.x",
            device_type_pattern="WS-C3850%",
            os_version_pattern="16.%",
            priority=100,
        )
        self.assertEqual(profile.priority, 100)
        self.assertIn("WS-C3850", str(profile))

    def test_switch_profile_default_priority(self):
        """Test that priority defaults to 100."""
        profile = SwitchProfile.objects.create(
            name="Default Priority Profile",
            device_type_pattern="WS-C%",
            os_version_pattern="15.%",
        )
        self.assertEqual(profile.priority, 100)

    def test_switch_profile_ordering(self):
        """Test profiles are ordered by priority then name."""
        SwitchProfile.objects.create(
            name="Low Priority",
            device_type_pattern="WS-C%",
            os_version_pattern="15.%",
            priority=50,
        )
        SwitchProfile.objects.create(
            name="High Priority",
            device_type_pattern="WS-C%",
            os_version_pattern="16.%",
            priority=10,
        )
        SwitchProfile.objects.create(
            name="Same Priority A",
            device_type_pattern="WS-C%",
            os_version_pattern="17.%",
            priority=50,
        )
        
        profiles = list(SwitchProfile.objects.all())
        self.assertEqual(profiles[0].name, "High Priority")
        self.assertEqual(profiles[1].name, "Low Priority")
        self.assertEqual(profiles[2].name, "Same Priority A")


class ConfigTemplateModelTest(TestCase):
    """Test cases for the ConfigTemplate model."""

    def setUp(self):
        """Set up test data."""
        self.service = PortService.objects.create(name="Test-Service")
        self.profile = SwitchProfile.objects.create(
            name="Test Profile",
            device_type_pattern="WS-C%",
            os_version_pattern="15.%",
        )

    def test_create_config_template(self):
        """Test creating a ConfigTemplate."""
        template = ConfigTemplate.objects.create(
            service=self.service,
            switch_profile=self.profile,
            instance=1,
            version=1,
            template_text="switchport mode access\nswitchport access vlan __VLAN__",
        )
        self.assertIn("Test-Service", str(template))
        self.assertEqual(template.version, 1)

    def test_template_versioning(self):
        """Test template versioning with instance/version."""
        # Create first version
        template_v1 = ConfigTemplate.objects.create(
            service=self.service,
            switch_profile=self.profile,
            instance=1,
            version=1,
            template_text="Version 1 config",
        )
        
        # Create second version of same instance
        template_v2 = ConfigTemplate.objects.create(
            service=self.service,
            switch_profile=self.profile,
            instance=1,
            version=2,
            template_text="Version 2 config",
        )
        
        self.assertEqual(template_v1.instance, template_v2.instance)
        self.assertNotEqual(template_v1.version, template_v2.version)

    def test_template_unique_instance_version(self):
        """Test that instance+version combination must be unique."""
        ConfigTemplate.objects.create(
            service=self.service,
            switch_profile=self.profile,
            instance=1,
            version=1,
            template_text="First template",
        )
        
        with self.assertRaises(IntegrityError):
            ConfigTemplate.objects.create(
                service=self.service,
                switch_profile=self.profile,
                instance=1,
                version=1,
                template_text="Duplicate",
            )


class MACAddressModelTest(TestCase):
    """Test cases for the MACAddress model."""

    def test_mac_normalization_dashes(self):
        """Test MAC address normalization with dashes."""
        mac = MACAddress.objects.create(
            address="aa-bb-cc-dd-ee-ff",
            mac_type=MACAddress.MACTypeChoices.ENDPOINT,
        )
        self.assertEqual(mac.address, "AA:BB:CC:DD:EE:FF")

    def test_mac_normalization_lowercase(self):
        """Test MAC address normalization from lowercase."""
        mac = MACAddress.objects.create(
            address="aa:bb:cc:dd:ee:ff",
            mac_type=MACAddress.MACTypeChoices.ENDPOINT,
        )
        self.assertEqual(mac.address, "AA:BB:CC:DD:EE:FF")

    def test_mac_unique(self):
        """Test that MAC addresses must be unique."""
        MACAddress.objects.create(address="AA:BB:CC:DD:EE:FF")
        with self.assertRaises(IntegrityError):
            MACAddress.objects.create(address="AA:BB:CC:DD:EE:FF")

    def test_mac_type_choices(self):
        """Test MAC type choices."""
        for mac_type in MACAddress.MACTypeChoices.values:
            mac = MACAddress.objects.create(
                address=f"AA:BB:CC:DD:EE:{mac_type[:2].upper()}",
                mac_type=mac_type,
            )
            self.assertEqual(mac.mac_type, mac_type)

    def test_mac_default_type(self):
        """Test that default MAC type is unknown."""
        mac = MACAddress.objects.create(address="11:22:33:44:55:66")
        self.assertEqual(mac.mac_type, MACAddress.MACTypeChoices.UNKNOWN)

    def test_mac_str_representation(self):
        """Test string representation is the address."""
        mac = MACAddress.objects.create(address="AA:BB:CC:DD:EE:FF")
        self.assertEqual(str(mac), "AA:BB:CC:DD:EE:FF")


class ControlSettingModelTest(TestCase):
    """Test cases for the ControlSetting model."""

    def test_create_control_setting(self):
        """Test creating a control setting."""
        setting = ControlSetting.objects.create(
            name="test_setting",
            value="test_value",
            description="Test description",
        )
        self.assertEqual(str(setting), "test_setting: test_value")

    def test_is_enabled_true_values(self):
        """Test is_enabled with various true values."""
        true_values = ["true", "yes", "enable", "enabled", "on", "1", "TRUE", "Yes"]
        for i, value in enumerate(true_values):
            ControlSetting.objects.create(name=f"test_setting_{i}", value=value)
            self.assertTrue(
                ControlSetting.is_enabled(f"test_setting_{i}"),
                f"Failed for value: {value}"
            )

    def test_is_enabled_false_values(self):
        """Test is_enabled with various false values."""
        false_values = ["false", "no", "disable", "disabled", "off", "0", "FALSE", "No"]
        for i, value in enumerate(false_values):
            ControlSetting.objects.create(name=f"test_false_{i}", value=value)
            self.assertFalse(
                ControlSetting.is_enabled(f"test_false_{i}"),
                f"Failed for value: {value}"
            )

    def test_is_enabled_default(self):
        """Test is_enabled returns default when setting doesn't exist."""
        self.assertFalse(ControlSetting.is_enabled("nonexistent"))
        self.assertTrue(ControlSetting.is_enabled("nonexistent", default=True))

    def test_get_value(self):
        """Test get_value retrieves setting value."""
        ControlSetting.objects.create(name="get_test", value="my_value")
        self.assertEqual(ControlSetting.get_value("get_test"), "my_value")

    def test_get_value_default(self):
        """Test get_value returns default for missing setting."""
        self.assertEqual(ControlSetting.get_value("missing", "default"), "default")
        self.assertEqual(ControlSetting.get_value("missing"), "")

    def test_set_value_create(self):
        """Test set_value creates new setting."""
        setting = ControlSetting.set_value("new_setting", "value1", "Description")
        self.assertEqual(setting.value, "value1")
        self.assertEqual(setting.description, "Description")

    def test_set_value_update(self):
        """Test set_value updates existing setting."""
        ControlSetting.objects.create(name="update_test", value="old_value")
        setting = ControlSetting.set_value("update_test", "new_value")
        self.assertEqual(setting.value, "new_value")
        
        # Should only be one record
        self.assertEqual(ControlSetting.objects.filter(name="update_test").count(), 1)

    def test_unique_name(self):
        """Test that setting names must be unique."""
        ControlSetting.objects.create(name="unique_name", value="value1")
        with self.assertRaises(IntegrityError):
            ControlSetting.objects.create(name="unique_name", value="value2")
