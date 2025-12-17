"""Tests for NetAccess template tags."""

from django.test import TestCase

from nautobot_network_provisioning.templatetags.netaccess_tags import (
    format_mac,
    mac_vendor_prefix,
    work_queue_status_badge,
    mac_type_badge,
)


class FormatMACFilterTest(TestCase):
    """Test cases for format_mac filter."""

    def test_format_mac_with_colons(self):
        """Test formatting MAC already with colons."""
        result = format_mac("aa:bb:cc:dd:ee:ff")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_format_mac_with_dashes(self):
        """Test formatting MAC with dashes."""
        result = format_mac("AA-BB-CC-DD-EE-FF")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_format_mac_with_dots(self):
        """Test formatting MAC with dots (Cisco format)."""
        result = format_mac("aabb.ccdd.eeff")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_format_mac_no_separator(self):
        """Test formatting MAC with no separator."""
        result = format_mac("aabbccddeeff")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_format_mac_empty(self):
        """Test formatting empty MAC."""
        result = format_mac("")
        self.assertEqual(result, "")
        
        result = format_mac(None)
        self.assertEqual(result, "")

    def test_format_mac_invalid_length(self):
        """Test formatting invalid length MAC."""
        result = format_mac("AABBCC")
        self.assertEqual(result, "AABBCC")  # Returns as-is


class MACVendorPrefixFilterTest(TestCase):
    """Test cases for mac_vendor_prefix filter."""

    def test_vendor_prefix(self):
        """Test extracting vendor prefix."""
        result = mac_vendor_prefix("AA:BB:CC:DD:EE:FF")
        self.assertEqual(result, "AA:BB:CC")

    def test_vendor_prefix_lowercase(self):
        """Test extracting vendor prefix from lowercase."""
        result = mac_vendor_prefix("aa:bb:cc:dd:ee:ff")
        self.assertEqual(result, "AA:BB:CC")

    def test_vendor_prefix_with_dashes(self):
        """Test extracting vendor prefix with dashes."""
        result = mac_vendor_prefix("AA-BB-CC-DD-EE-FF")
        self.assertEqual(result, "AA:BB:CC")

    def test_vendor_prefix_empty(self):
        """Test with empty input."""
        result = mac_vendor_prefix("")
        self.assertEqual(result, "")
        
        result = mac_vendor_prefix(None)
        self.assertEqual(result, "")

    def test_vendor_prefix_short_mac(self):
        """Test with too short MAC."""
        result = mac_vendor_prefix("AA:BB")
        self.assertEqual(result, "")


class WorkQueueStatusBadgeTest(TestCase):
    """Test cases for work_queue_status_badge tag."""

    def test_pending_status(self):
        """Test pending status badge."""
        result = work_queue_status_badge("pending")
        self.assertEqual(result, "bg-warning")

    def test_in_progress_status(self):
        """Test in_progress status badge."""
        result = work_queue_status_badge("in_progress")
        self.assertEqual(result, "bg-info")

    def test_completed_status(self):
        """Test completed status badge."""
        result = work_queue_status_badge("completed")
        self.assertEqual(result, "bg-success")

    def test_failed_status(self):
        """Test failed status badge."""
        result = work_queue_status_badge("failed")
        self.assertEqual(result, "bg-danger")

    def test_cancelled_status(self):
        """Test cancelled status badge."""
        result = work_queue_status_badge("cancelled")
        self.assertEqual(result, "bg-secondary")

    def test_unknown_status(self):
        """Test unknown status falls back to secondary."""
        result = work_queue_status_badge("unknown")
        self.assertEqual(result, "bg-secondary")


class MACTypeBadgeTest(TestCase):
    """Test cases for mac_type_badge tag."""

    def test_interface_type(self):
        """Test interface MAC type badge."""
        result = mac_type_badge("interface")
        self.assertEqual(result, "bg-primary")

    def test_endpoint_type(self):
        """Test endpoint MAC type badge."""
        result = mac_type_badge("endpoint")
        self.assertEqual(result, "bg-success")

    def test_virtual_type(self):
        """Test virtual MAC type badge."""
        result = mac_type_badge("virtual")
        self.assertEqual(result, "bg-info")

    def test_unknown_type(self):
        """Test unknown MAC type badge."""
        result = mac_type_badge("unknown")
        self.assertEqual(result, "bg-secondary")

    def test_invalid_type(self):
        """Test invalid MAC type falls back to secondary."""
        result = mac_type_badge("invalid")
        self.assertEqual(result, "bg-secondary")
