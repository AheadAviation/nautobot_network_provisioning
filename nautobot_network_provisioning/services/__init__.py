"""Services module for NetAccess app."""

from nautobot_network_provisioning.services.jack_lookup import (
    find_interface_by_jack,
    find_interface_unified,
    find_interface_via_frontport,
    JackLookupResult,
)
from nautobot_network_provisioning.services.template_matcher import (
    find_template_for_device,
    find_all_matching_profiles,
    get_device_model,
    get_device_os_version,
)
from nautobot_network_provisioning.services.template_renderer import (
    render_template,
    render_twix_variables,
    render_jinja2_template,
    get_available_variables,
    validate_template,
)
from nautobot_network_provisioning.services.config_push import (
    push_interface_config,
    test_device_connection,
    get_interface_running_config,
)
from nautobot_network_provisioning.services.proxy_worker import (
    get_proxy_client,
    proxy_execute_command,
    proxy_get_mac_table,
    proxy_get_arp_table,
    proxy_ping,
    test_proxy_connection,
    ProxyWorkerClient,
    ProxyWorkerConfig,
)

__all__ = [
    # Jack lookup
    "find_interface_by_jack",
    "find_interface_unified",
    "find_interface_via_frontport",
    "JackLookupResult",
    # Template matching
    "find_template_for_device",
    "find_all_matching_profiles",
    "get_device_model",
    "get_device_os_version",
    # Template rendering
    "render_template",
    "render_twix_variables",
    "render_jinja2_template",
    "get_available_variables",
    "validate_template",
    # Config push
    "push_interface_config",
    "test_device_connection",
    "get_interface_running_config",
    # Proxy worker
    "get_proxy_client",
    "proxy_execute_command",
    "proxy_get_mac_table",
    "proxy_get_arp_table",
    "proxy_ping",
    "test_proxy_connection",
    "ProxyWorkerClient",
    "ProxyWorkerConfig",
]
