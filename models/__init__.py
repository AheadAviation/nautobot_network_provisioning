"""Models for the NetAccess app."""

from nautobot_network_provisioning.models.config import (
    PortService,
    AutomatedTask,  # Alias for PortService
    SwitchProfile,
    ConfigTemplate,
    ConfigTemplateHistory,
)
from nautobot_network_provisioning.models.jack import JackMapping
from nautobot_network_provisioning.models.queue import WorkQueueEntry
from nautobot_network_provisioning.models.mac import MACAddress, MACAddressEntry, MACAddressHistory
from nautobot_network_provisioning.models.arp import ARPEntry
from nautobot_network_provisioning.models.system import ControlSetting

__all__ = [
    # Configuration models
    "PortService",  # Legacy name (kept for backward compatibility)
    "AutomatedTask",  # New name (alias for PortService)
    "SwitchProfile",
    "ConfigTemplate",
    "ConfigTemplateHistory",
    # Jack mapping
    "JackMapping",
    # Work queue
    "WorkQueueEntry",
    # MAC tracking
    "MACAddress",
    "MACAddressEntry",
    "MACAddressHistory",
    # ARP
    "ARPEntry",
    # System
    "ControlSetting",
]
