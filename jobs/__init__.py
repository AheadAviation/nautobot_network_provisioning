"""Jobs module for NetAccess app."""

from nautobot_network_provisioning.jobs.queue_processor import WorkQueueProcessor, WorkQueueConnectionTest
from nautobot_network_provisioning.jobs.mac_collector import MACAddressCollector
from nautobot_network_provisioning.jobs.arp_collector import ARPCollector
from nautobot_network_provisioning.jobs.history_archiver import MACHistoryArchiver
from nautobot_network_provisioning.jobs.jack_import import JackMappingImport
from nautobot_network_provisioning.jobs.proxy_collector import (
    ProxyConnectionTest,
    ProxyMACCollector,
    ProxyDeviceCommand,
)
from nautobot_network_provisioning.jobs.demo_data_loader import LoadDemoData
from nautobot_network_provisioning.jobs.work_queue_import import WorkQueueBulkImport

jobs = [
    # Work Queue Processing
    WorkQueueProcessor,
    WorkQueueConnectionTest,
    WorkQueueBulkImport,
    
    # MAC/ARP Collection
    MACAddressCollector,
    ARPCollector,
    MACHistoryArchiver,
    
    # Import Jobs
    JackMappingImport,
    LoadDemoData,
    
    # Proxy Worker Jobs
    ProxyConnectionTest,
    ProxyMACCollector,
    ProxyDeviceCommand,
]

__all__ = [
    # Work Queue
    "WorkQueueProcessor",
    "WorkQueueConnectionTest",
    "WorkQueueBulkImport",
    
    # MAC/ARP
    "MACAddressCollector",
    "ARPCollector",
    "MACHistoryArchiver",
    
    # Import
    "JackMappingImport",
    "LoadDemoData",
    
    # Proxy
    "ProxyConnectionTest",
    "ProxyMACCollector",
    "ProxyDeviceCommand",
    
    "jobs",
]
