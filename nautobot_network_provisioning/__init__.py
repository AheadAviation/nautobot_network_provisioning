"""
Network Provisioning - provisioning platform for Nautobot (docs/design.md).

This repository is a net-new implementation aligned to the design docs:
- Task Catalog (TaskDefinition) + Task Implementations (TaskImplementation)
- Workflows (Workflow + WorkflowStep)
- Executions (Execution + ExecutionStep)
- Providers (Provider + ProviderConfig)
"""

__version__ = "0.2.0"

# NOTE: GitHub Actions (release/version checks) imports this package in a plain
# Python environment that may not have Nautobot installed. Keep version importable
# without requiring Nautobot at import-time.
try:
    from nautobot.apps import NautobotAppConfig  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    NautobotAppConfig = object  # type: ignore[misc,assignment]


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
        # Phase 2 will introduce async execution via Jobs/Celery.
        "enable_async_execution": False,
    }
    # This app does not override any core Nautobot views. Setting this explicitly avoids Nautobot attempting
    # to import our `views.py` during startup for "override view" registration.
    override_views = None

    @property
    def template_extensions(self):
        from nautobot_network_provisioning.template_content import template_extensions
        return template_extensions


config = NetworkProvisioningConfig
