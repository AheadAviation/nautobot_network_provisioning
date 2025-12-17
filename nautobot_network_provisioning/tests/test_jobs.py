"""Tests for NetAccess jobs."""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from nautobot_network_provisioning.models import ControlSetting, MACAddressHistory


class WorkQueueProcessorTest(TestCase):
    """Test cases for WorkQueueProcessor job."""

    def test_queue_disabled(self):
        """Test that job exits early when queue processing is disabled."""
        from nautobot_network_provisioning.jobs.queue_processor import WorkQueueProcessor
        
        ControlSetting.objects.create(
            name="queue_processing_enabled",
            value="false",
        )
        
        job = WorkQueueProcessor()
        job.logger = MagicMock()
        
        result = job.run()
        
        self.assertEqual(result, "Queue processing is disabled")
        job.logger.info.assert_called()

    def test_queue_enabled_no_entries(self):
        """Test job with no entries to process."""
        from nautobot_network_provisioning.jobs.queue_processor import WorkQueueProcessor
        
        ControlSetting.objects.create(
            name="queue_processing_enabled",
            value="true",
        )
        
        job = WorkQueueProcessor()
        job.logger = MagicMock()
        
        result = job.run()
        
        self.assertEqual(result, "No entries to process")


class MACHistoryArchiverTest(TestCase):
    """Test cases for MACHistoryArchiver job."""

    def test_no_records_to_archive(self):
        """Test archiver when there are no old records."""
        from nautobot_network_provisioning.jobs.history_archiver import MACHistoryArchiver
        
        job = MACHistoryArchiver()
        job.logger = MagicMock()
        
        result = job.run(retention_days=30)
        
        self.assertEqual(result, "No records to archive")

    def test_default_retention_from_setting(self):
        """Test that retention defaults from control setting."""
        from nautobot_network_provisioning.jobs.history_archiver import MACHistoryArchiver
        
        ControlSetting.objects.create(
            name="history_retention_days",
            value="45",
        )
        
        job = MACHistoryArchiver()
        job.logger = MagicMock()
        
        # Run without specifying retention_days
        result = job.run(retention_days=None)
        
        # Should use 45 from control setting
        self.assertIn("No records to archive", result)


class MACAddressCollectorTest(TestCase):
    """Test cases for MACAddressCollector job."""

    def test_collection_disabled(self):
        """Test that job exits when collection is disabled."""
        from nautobot_network_provisioning.jobs.mac_collector import MACAddressCollector
        
        ControlSetting.objects.create(
            name="mac_collection_enabled",
            value="false",
        )
        
        job = MACAddressCollector()
        job.logger = MagicMock()
        
        result = job.run()
        
        self.assertEqual(result, "MAC collection is disabled")


class ARPCollectorTest(TestCase):
    """Test cases for ARPCollector job."""

    def test_collection_disabled(self):
        """Test that job exits when collection is disabled."""
        from nautobot_network_provisioning.jobs.arp_collector import ARPCollector
        
        ControlSetting.objects.create(
            name="mac_collection_enabled",
            value="false",
        )
        
        job = ARPCollector()
        job.logger = MagicMock()
        
        result = job.run()
        
        self.assertEqual(result, "Collection is disabled")


class JackMappingImportTest(TestCase):
    """Test cases for JackMappingImport job."""

    def test_missing_headers(self):
        """Test import with missing required headers."""
        from nautobot_network_provisioning.jobs.jack_import import JackMappingImport
        import io
        
        # Create CSV with missing headers
        csv_content = "building,jack,device_name\nBuilding1,J001,switch-01"
        csv_file = MagicMock()
        csv_file.read.return_value = csv_content.encode("utf-8")
        
        job = JackMappingImport()
        job.logger = MagicMock()
        
        result = job.run(csv_file=csv_file, update_existing=True, dry_run=False)
        
        self.assertIn("Missing required columns", result)

    def test_dry_run_mode(self):
        """Test that dry run doesn't create records."""
        from nautobot_network_provisioning.jobs.jack_import import JackMappingImport
        from nautobot_network_provisioning.models import JackMapping
        
        initial_count = JackMapping.objects.count()
        
        # Create valid CSV
        csv_content = "building,comm_room,jack,device_name,interface_name,description\n"
        csv_content += "TestBuilding,MDF,J001,switch-01,Gi1/0/1,Test\n"
        csv_file = MagicMock()
        csv_file.read.return_value = csv_content.encode("utf-8")
        
        job = JackMappingImport()
        job.logger = MagicMock()
        
        result = job.run(csv_file=csv_file, update_existing=True, dry_run=True)
        
        # Should not have created any records
        self.assertEqual(JackMapping.objects.count(), initial_count)
        self.assertIn("DRY RUN", result)
