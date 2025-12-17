"""
Network Provisioning - Port Configuration Automation and MAC Tracking for Nautobot.

This app provides:
- Port Configuration: Services, templates, scheduled config changes via work queue
- Jack Mapping: Custom table mapping Building/Room/Jack to Device/Interface
- MAC Tracking: Track MAC addresses, CAM tables, ARP entries with 30-day history
- Demo Data: Optional demo data loading to help users understand the app

Migration from TWIX:
This app is a modernized version of the legacy TWIX (Network Access Configuration Tool).
All TWIX functionality has been preserved and enhanced with Nautobot integration.

Configuration Templates:
All configuration templates are stored in the database and editable via the Nautobot GUI.
Templates support both Jinja2 syntax ({{ variable }}) and legacy TWIX syntax (__VAR__).

To get started, run the "Load Demo Data" job to populate example services, profiles,
and templates based on the original TWIX tool.
"""

from nautobot.apps import NautobotAppConfig

__version__ = "0.1.1"


class NetworkProvisioningConfig(NautobotAppConfig):
    """Nautobot App configuration for Network Provisioning."""

    name = "nautobot_network_provisioning"
    verbose_name = "Network Provisioning"
    description = "Port Configuration Automation and MAC Address Tracking"
    version = __version__
    author = "Network Operations"
    author_email = "netops@example.com"
    base_url = "network-provisioning"
    min_version = "2.0.0"
    max_version = "2.99"
    required_settings = []
    default_settings = {
        # =========================================================================
        # WORK QUEUE PROCESSING
        # =========================================================================
        # Master switch to enable/disable work queue processing
        "queue_processing_enabled": True,
        
        # Whether to run 'write mem' after pushing configuration
        "write_mem_enabled": True,
        
        # Whether to backup interface config before making changes
        "config_backup_enabled": True,
        
        # Default to dry-run mode for new work queue entries (safety first)
        "dry_run_default": True,
        
        # Maximum number of entries to process per job run
        "max_queue_entries_per_run": 50,
        
        # =========================================================================
        # MAC ADDRESS COLLECTION
        # =========================================================================
        # Enable MAC address collection jobs
        "mac_collection_enabled": True,
        
        # Number of days to retain MAC address history
        "history_retention_days": 30,
        
        # =========================================================================
        # DEMO DATA SETTINGS
        # =========================================================================
        # Master switch to enable/disable demo-data features and the demo data job UI.
        # Demo data is still loaded only when the "Load Demo Data" job is executed.
        "demo_data": False,
        
        # Set to True to show a reminder to load demo data on fresh install
        # The actual loading is done via the "Load Demo Data" job
        "show_demo_data_reminder": True,
        
        # Default data set for demo data loader: "full", "minimal", or "utility_only"
        "demo_data_default_set": "full",
        
        # =========================================================================
        # TEMPLATE SETTINGS
        # =========================================================================
        # Templates are stored in the database (ConfigTemplate model)
        # These settings are for optional file-based template loading
        "template_directory": "/opt/nautobot/templates",
        
        # Whether to validate Jinja2 syntax when saving templates
        "validate_templates_on_save": True,
        
        # =========================================================================
        # NOTIFICATION SETTINGS
        # =========================================================================
        # Enable email notifications for work queue status changes
        "notifications_enabled": False,
        
        # Email addresses to notify (comma-separated)
        "notification_recipients": "",
    }

    def ready(self):
        """Callback when the app is ready."""
        super().ready()
        
        # Check if demo data reminder should be shown
        self._check_demo_data_reminder()
        # If demo data features are enabled, auto-enable the demo loader job for convenience.
        self._ensure_demo_job_enabled()
    
    def _check_demo_data_reminder(self):
        """
        Check if demo data reminder should be shown.
        
        Shows a log message if:
        1. show_demo_data_reminder setting is True
        2. No PortService records exist (fresh install)
        """
        from django.conf import settings
        
        try:
            # Get app settings
            app_settings = getattr(settings, "PLUGINS_CONFIG", {}).get("nautobot_network_provisioning", {})
            show_reminder = app_settings.get("show_demo_data_reminder", True)
            
            if not show_reminder:
                return
            
            # Check if any PortService exists (indicator of existing data)
            from nautobot_network_provisioning.models import PortService
            if PortService.objects.exists():
                return
            
            # Log reminder to load demo data
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                "Network Provisioning: Database appears empty. "
                "Run the 'Load Demo Data' job (Jobs > Network Provisioning > Load Demo Data) "
                "to populate example Port Services, Switch Profiles, and Config Templates. "
                "All templates are stored in the database and editable via the GUI."
            )
        except Exception:
            # Silently fail during app initialization
            pass

    def _ensure_demo_job_enabled(self):
        """Auto-enable the demo loader job when demo_data is enabled."""

        from django.conf import settings

        try:
            app_settings = getattr(settings, "PLUGINS_CONFIG", {}).get("nautobot_network_provisioning", {})
            if not app_settings.get("demo_data", False):
                return

            from nautobot.extras.models import Job

            Job.objects.filter(
                module_name="nautobot_network_provisioning.jobs.demo_data_loader",
                job_class_name="LoadDemoData",
            ).update(enabled=True)
        except Exception:
            # Silently fail during app initialization
            return


config = NetworkProvisioningConfig
