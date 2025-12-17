"""Tests for NetAccess services."""

from django.test import TestCase
from unittest.mock import MagicMock, patch

from nautobot_network_provisioning.services.template_matcher import (
    _sql_like_to_regex,
    _pattern_match,
    get_device_model,
    get_device_os_version,
)
from nautobot_network_provisioning.services.template_renderer import (
    render_template,
    validate_template,
    get_available_variables,
    TEMPLATE_VARIABLES,
)


class SQLLikeToRegexTest(TestCase):
    """Test cases for SQL LIKE to regex conversion."""

    def test_percent_wildcard(self):
        """Test % wildcard conversion."""
        regex = _sql_like_to_regex("WS-C3850%")
        self.assertEqual(regex, "^WS\\-C3850.*$")

    def test_underscore_wildcard(self):
        """Test _ wildcard conversion."""
        regex = _sql_like_to_regex("WS-C385_")
        self.assertEqual(regex, "^WS\\-C385.$")

    def test_multiple_wildcards(self):
        """Test multiple wildcards."""
        regex = _sql_like_to_regex("WS-%-%")
        self.assertEqual(regex, "^WS\\-.*\\-.*$")

    def test_parentheses_in_pattern(self):
        """Test patterns with parentheses."""
        regex = _sql_like_to_regex("15.2(%)E%")
        # Parentheses should be escaped
        self.assertIn(r"\(", regex)
        self.assertIn(r"\)", regex)

    def test_no_wildcards(self):
        """Test pattern with no wildcards."""
        regex = _sql_like_to_regex("exact-match")
        self.assertEqual(regex, "^exact\\-match$")


class PatternMatchTest(TestCase):
    """Test cases for pattern matching."""

    def test_simple_match(self):
        """Test simple pattern matching."""
        self.assertTrue(_pattern_match("WS-C3850-24T", "WS-C3850%"))
        self.assertTrue(_pattern_match("WS-C3850-48P", "WS-C3850%"))
        self.assertFalse(_pattern_match("WS-C2960X", "WS-C3850%"))

    def test_version_pattern(self):
        """Test version pattern matching."""
        self.assertTrue(_pattern_match("15.2(3)E2", "15.2(%)E%"))
        self.assertTrue(_pattern_match("15.2(7)E1", "15.2(%)E%"))
        self.assertFalse(_pattern_match("15.0(2)SE", "15.2(%)E%"))

    def test_simple_version(self):
        """Test simple version matching."""
        self.assertTrue(_pattern_match("16.12.4", "16.%"))
        self.assertTrue(_pattern_match("16.3.1", "16.%"))
        self.assertFalse(_pattern_match("15.2", "16.%"))

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        self.assertTrue(_pattern_match("ws-c3850-24t", "WS-C3850%"))
        self.assertTrue(_pattern_match("WS-C3850-24T", "ws-c3850%"))

    def test_empty_values(self):
        """Test with empty values."""
        self.assertFalse(_pattern_match("", "WS-%"))
        self.assertFalse(_pattern_match("WS-C3850", ""))
        self.assertFalse(_pattern_match("", ""))
        self.assertFalse(_pattern_match(None, "WS-%"))
        self.assertFalse(_pattern_match("WS-C3850", None))


class DeviceModelExtractionTest(TestCase):
    """Test cases for device model extraction."""

    def test_get_device_model_with_type(self):
        """Test extracting model from device with device_type."""
        device = MagicMock()
        device.device_type.model = "WS-C3850-24T"
        
        result = get_device_model(device)
        self.assertEqual(result, "WS-C3850-24T")

    def test_get_device_model_c9300_normalization(self):
        """Test C9300 model normalization."""
        device = MagicMock()
        device.device_type.model = "C9300-48P"
        
        result = get_device_model(device)
        self.assertEqual(result, "WS-C9300-48P")

    def test_get_device_model_no_type(self):
        """Test with device without device_type."""
        device = MagicMock()
        device.device_type = None
        
        result = get_device_model(device)
        self.assertEqual(result, "")


class DeviceOSVersionExtractionTest(TestCase):
    """Test cases for device OS version extraction."""

    def test_get_os_version_from_custom_field(self):
        """Test extracting OS version from custom field."""
        device = MagicMock()
        device.custom_field_data = {"os_version": "16.12.4"}
        
        result = get_device_os_version(device)
        self.assertEqual(result, "16.12.4")

    def test_get_os_version_alternative_field_names(self):
        """Test alternative custom field names."""
        for field_name in ["software_version", "ios_version", "version"]:
            device = MagicMock()
            device.custom_field_data = {field_name: "15.2(3)E2"}
            
            result = get_device_os_version(device)
            self.assertEqual(result, "15.2(3)E2", f"Failed for field: {field_name}")

    def test_get_os_version_no_custom_field(self):
        """Test with no custom field data."""
        device = MagicMock()
        device.custom_field_data = {}
        
        result = get_device_os_version(device)
        self.assertEqual(result, "")


class TemplateValidationTest(TestCase):
    """Test cases for template validation."""

    def test_validate_template_valid(self):
        """Test validation with known variables."""
        template = "interface __INTERFACE__\n description __BUILDING__/__JACK__"
        result = validate_template(template)
        
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["unknown_variables"]), 0)
        self.assertIn("__INTERFACE__", result["found_variables"])
        self.assertIn("__BUILDING__", result["found_variables"])
        self.assertIn("__JACK__", result["found_variables"])

    def test_validate_template_unknown_variable(self):
        """Test validation with unknown variables."""
        template = "interface __INTERFACE__\n custom __UNKNOWN_VAR__"
        result = validate_template(template)
        
        self.assertFalse(result["valid"])
        self.assertIn("__UNKNOWN_VAR__", result["unknown_variables"])

    def test_validate_template_multiple_unknown(self):
        """Test validation with multiple unknown variables."""
        template = "__FOO__ and __BAR__ and __INTERFACE__"
        result = validate_template(template)
        
        self.assertFalse(result["valid"])
        self.assertEqual(len(result["unknown_variables"]), 2)
        self.assertIn("__FOO__", result["unknown_variables"])
        self.assertIn("__BAR__", result["unknown_variables"])

    def test_validate_template_empty(self):
        """Test validation with empty template."""
        result = validate_template("")
        
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["found_variables"]), 0)

    def test_validate_template_no_variables(self):
        """Test validation with no variables."""
        template = "switchport mode access\nswitchport access vlan 100"
        result = validate_template(template)
        
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["found_variables"]), 0)


class AvailableVariablesTest(TestCase):
    """Test cases for available variables."""

    def test_get_available_variables(self):
        """Test getting available variables."""
        variables = get_available_variables()
        
        # Check required variables exist
        required_vars = [
            "__INTERFACE__",
            "__BUILDING__",
            "__SWITCH__",
            "__DATE_APPLIED__",
            "__SERVICE__",
            "__JACK__",
            "__COMM_ROOM__",
        ]
        
        for var in required_vars:
            self.assertIn(var, variables, f"Missing variable: {var}")

    def test_variable_descriptions(self):
        """Test that all variables have descriptions."""
        variables = get_available_variables()
        
        for var, description in variables.items():
            self.assertIsInstance(description, str)
            self.assertTrue(len(description) > 0, f"Empty description for {var}")


class TemplateRenderingTest(TestCase):
    """Test cases for template rendering."""

    def test_render_simple_template(self):
        """Test rendering a simple template."""
        device = MagicMock()
        device.name = "switch-01"
        
        interface = MagicMock()
        interface.name = "GigabitEthernet1/0/1"
        
        service = MagicMock()
        service.name = "Access-VoIP"
        
        template = "interface __INTERFACE__\n description Connected to __SWITCH__"
        
        result = render_template(
            template_text=template,
            device=device,
            interface=interface,
            service=service,
        )
        
        self.assertIn("GigabitEthernet1/0/1", result)
        self.assertIn("switch-01", result)
        self.assertNotIn("__INTERFACE__", result)
        self.assertNotIn("__SWITCH__", result)

    def test_render_with_building_info(self):
        """Test rendering with building information."""
        device = MagicMock()
        device.name = "switch-01"
        
        interface = MagicMock()
        interface.name = "Gi1/0/1"
        
        service = MagicMock()
        service.name = "Access-Data"
        
        building = MagicMock()
        building.name = "Science Building"
        
        template = "description __BUILDING__/__COMM_ROOM__/__JACK__"
        
        result = render_template(
            template_text=template,
            device=device,
            interface=interface,
            service=service,
            building=building,
            comm_room="040",
            jack="0228",
        )
        
        self.assertIn("Science Building", result)
        self.assertIn("040", result)
        self.assertIn("0228", result)

    def test_render_preserves_unknown_text(self):
        """Test that non-variable text is preserved."""
        device = MagicMock()
        device.name = "switch-01"
        
        interface = MagicMock()
        interface.name = "Gi1/0/1"
        
        service = MagicMock()
        service.name = "Test"
        
        template = "switchport mode access\nswitchport access vlan 100\nspanning-tree portfast"
        
        result = render_template(
            template_text=template,
            device=device,
            interface=interface,
            service=service,
        )
        
        self.assertIn("switchport mode access", result)
        self.assertIn("switchport access vlan 100", result)
        self.assertIn("spanning-tree portfast", result)
