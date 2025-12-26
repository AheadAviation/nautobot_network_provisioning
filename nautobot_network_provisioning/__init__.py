"""Nautobot App: nautobot_network_provisioning."""

__version__ = "0.2.0"

try:
    from nautobot.apps import NautobotAppConfig
except ImportError:
    # Fallback for non-Nautobot environments (e.g., CI)
    NautobotAppConfig = object


class NetworkProvisioningConfig(NautobotAppConfig):
    """Nautobot App configuration for Network Provisioning."""

    name = "nautobot_network_provisioning"
    verbose_name = "Network Provisioning"
    description = "Automation authoring and execution platform for Nautobot (Tasks, Workflows, Executions)."
    version = __version__
    author = "Network Operations"
    author_email = "netops@example.com"
    base_url = "network-provisioning"
    min_version = "2.0.0"
    max_version = "2.99"
    required_settings = []
    default_settings = {
        "enable_async_execution": False,
        "demo_data": False,
        "queue_processing_enabled": True,
        "write_mem_enabled": True,
        "mac_collection_enabled": True,
        "history_retention_days": 30,
        "proxy_worker_enabled": False,
        "proxy_broker_url": "redis://localhost:6379/0",
        "proxy_backend_url": "redis://localhost:6379/0",
        "proxy_queue_name": "proxy_queue",
        "proxy_task_timeout": 120,
    }

    def ready(self):
        super().ready()
        # Register template extensions (using function-level import to avoid circular dependencies)
        try:
            from .template_content import template_extensions
            self.template_extensions = template_extensions
        except ImportError as e:
            # Log but don't fail during reload verification
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not import template_extensions during ready(): {e}")
            self.template_extensions = []


config = NetworkProvisioningConfig

