"""MAC Address Collector job for collecting MAC address tables from devices."""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from django.db import transaction

from nautobot.apps.jobs import Job, ObjectVar, MultiObjectVar, ChoiceVar, register_jobs
from nautobot.dcim.models import Device, Interface, Location
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices

from nautobot_network_provisioning.models import MACAddress, MACAddressEntry, MACAddressHistory, ControlSetting


class MACAddressCollector(Job):
    """
    Collect MAC address tables from network devices.
    
    This job connects to devices and collects their MAC address tables,
    updating the MACAddress, MACAddressEntry, and MACAddressHistory tables.
    """

    device = ObjectVar(
        model=Device,
        required=False,
        description="Specific device to collect from (leave empty for all devices)",
    )
    location = ObjectVar(
        model=Location,
        required=False,
        description="Collect from devices in this location",
    )
    collection_method = ChoiceVar(
        choices=[
            ("cli", "CLI (show mac address-table)"),
            ("snmp", "SNMP (dot1dTpFdbTable)"),
            ("auto", "Auto-detect"),
        ],
        default="cli",
        description="Method to use for collecting MAC addresses",
    )

    class Meta:
        name = "MAC Address Collector"
        description = "Collect MAC address tables from network devices"
        has_sensitive_variables = False

    def run(self, device=None, location=None, collection_method="cli"):
        """Execute the MAC address collection."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            # Check if collection is enabled
            if not ControlSetting.is_enabled("mac_collection_enabled", default=True):
                self.logger.info("MAC collection is disabled")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("MAC collection is disabled", level_choice=LogLevelChoices.LOG_INFO)
                self.job_result.save()
                return "MAC collection is disabled"
            
            # Determine which devices to collect from
            devices = self._get_target_devices(device, location)
            
            if not devices:
                self.logger.warning("No devices found to collect from")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("No devices to collect from", level_choice=LogLevelChoices.LOG_WARNING)
                self.job_result.save()
                return "No devices to collect from"
            
            self.logger.info(f"Collecting MAC addresses from {len(devices)} devices")
            
            collected_total = 0
            errors = 0
            
            for dev in devices:
                try:
                    count = self._collect_from_device(dev, collection_method)
                    collected_total += count
                    self.logger.info(f"Collected {count} MAC entries from {dev.name}")
                except Exception as e:
                    errors += 1
                    self.logger.error(f"Failed to collect from {dev.name}: {e}")
            
            summary = f"Collected {collected_total} MAC entries from {len(devices)} devices ({errors} errors)"
            self.logger.info(summary)
            
            # Mark job as SUCCESS
            self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
            self.job_result.log(summary, level_choice=LogLevelChoices.LOG_INFO)
            self.job_result.save()
            
            return summary

        except Exception as e:
            error_message = f"Job failed with error: {str(e)}"
            self.logger.error(error_message)
            self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
            self.job_result.log(error_message, level_choice=LogLevelChoices.LOG_ERROR)
            self.job_result.save()
            raise

    def _get_target_devices(self, device, location) -> List[Device]:
        """Get the list of devices to collect from."""
        if device:
            return [device]
        
        queryset = Device.objects.filter(
            status__name__in=["Active", "Staged"],
        ).exclude(
            platform__isnull=True,
        )
        
        if location:
            queryset = queryset.filter(location=location)
        
        return list(queryset)

    def _collect_from_device(self, device: Device, method: str) -> int:
        """Collect MAC addresses from a single device."""
        if method == "cli" or method == "auto":
            return self._collect_via_cli(device)
        elif method == "snmp":
            return self._collect_via_snmp(device)
        else:
            return self._collect_via_cli(device)

    def _collect_via_cli(self, device: Device) -> int:
        """Collect MAC addresses via CLI (show mac address-table)."""
        try:
            from netmiko import ConnectHandler
            from nautobot_network_provisioning.services.config_push import (
                get_device_credentials,
                get_device_platform,
            )
            
            username, password, secret = get_device_credentials(device)
            platform = get_device_platform(device)
            
            if device.primary_ip4:
                host = str(device.primary_ip4.host)
            elif device.primary_ip6:
                host = str(device.primary_ip6.host)
            else:
                self.logger.warning(f"No IP address for device {device.name}")
                return 0
            
            connection_params = {
                "device_type": platform,
                "host": host,
                "username": username,
                "password": password,
                "secret": secret,
                "timeout": 60,
            }
            
            with ConnectHandler(**connection_params) as conn:
                if secret:
                    conn.enable()
                
                # Get MAC address table
                output = conn.send_command("show mac address-table")
                
                # Parse and store entries
                entries = self._parse_mac_table(output, device)
                return self._store_mac_entries(entries, device)
                
        except ImportError:
            self.logger.error("Netmiko library not installed")
            return 0
        except Exception as e:
            self.logger.error(f"CLI collection failed for {device.name}: {e}")
            raise

    def _collect_via_snmp(self, device: Device) -> int:
        """Collect MAC addresses via SNMP."""
        # SNMP collection would be implemented here
        # For now, fall back to CLI
        self.logger.warning(f"SNMP not implemented, falling back to CLI for {device.name}")
        return self._collect_via_cli(device)

    def _parse_mac_table(self, output: str, device: Device) -> List[Dict[str, Any]]:
        """Parse MAC address table output from CLI."""
        entries = []
        
        # Common patterns for Cisco IOS/IOS-XE/NX-OS
        # Format: VLAN  MAC Address     Type    Ports
        patterns = [
            # Cisco IOS/IOS-XE
            r"^\s*(\d+)\s+([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})\s+(\w+)\s+(\S+)",
            # Alternative format
            r"^\s*(\d+)\s+([0-9a-fA-F:.-]+)\s+(\w+)\s+(\S+)",
        ]
        
        for line in output.split("\n"):
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    vlan = int(match.group(1))
                    mac = self._normalize_mac(match.group(2))
                    entry_type = match.group(3).lower()
                    port = match.group(4)
                    
                    # Skip CPU/Router entries
                    if port.lower() in ["cpu", "router", "switch"]:
                        continue
                    
                    entries.append({
                        "mac": mac,
                        "vlan": vlan,
                        "port": port,
                        "entry_type": entry_type,
                    })
                    break
        
        return entries

    def _normalize_mac(self, mac: str) -> str:
        """Normalize MAC address to XX:XX:XX:XX:XX:XX format."""
        # Remove separators and convert to uppercase
        mac_clean = re.sub(r"[.:-]", "", mac).upper()
        
        if len(mac_clean) != 12:
            return mac.upper()
        
        # Format as XX:XX:XX:XX:XX:XX
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))

    @transaction.atomic
    def _store_mac_entries(self, entries: List[Dict[str, Any]], device: Device) -> int:
        """Store MAC entries in the database."""
        now = datetime.now(timezone.utc)
        stored_count = 0
        
        # Get interface mapping for the device
        interface_map = {
            iface.name: iface
            for iface in Interface.objects.filter(device=device)
        }
        
        for entry in entries:
            mac_str = entry["mac"]
            port_name = entry["port"]
            vlan = entry["vlan"]
            entry_type = entry.get("entry_type", "dynamic")
            
            # Find the interface
            interface = interface_map.get(port_name)
            if not interface:
                # Try partial match for interface names
                for iface_name, iface in interface_map.items():
                    if port_name in iface_name or iface_name in port_name:
                        interface = iface
                        break
            
            if not interface:
                continue
            
            # Get or create MAC address record
            mac_obj, created = MACAddress.objects.get_or_create(
                address=mac_str,
                defaults={
                    "mac_type": MACAddress.MACTypeChoices.UNKNOWN,
                    "first_seen": now,
                }
            )
            
            # Update last seen info
            mac_obj.last_device = device
            mac_obj.last_interface = interface
            mac_obj.last_vlan = vlan
            mac_obj.last_seen = now
            if not mac_obj.first_seen:
                mac_obj.first_seen = now
            mac_obj.save()
            
            # Create or update current entry
            MACAddressEntry.objects.update_or_create(
                mac_address=mac_obj,
                device=device,
                interface=interface,
                vlan=vlan,
                defaults={
                    "entry_type": entry_type,
                }
            )
            
            # Update history
            self._update_history(mac_obj, device, interface, vlan, entry_type, now)
            
            stored_count += 1
        
        return stored_count

    def _update_history(
        self,
        mac: MACAddress,
        device: Device,
        interface: Interface,
        vlan: Optional[int],
        entry_type: str,
        timestamp: datetime,
    ):
        """Update MAC address history."""
        # Look for existing history record for this location
        history = MACAddressHistory.objects.filter(
            mac_address=mac,
            device=device,
            interface=interface,
            vlan=vlan,
        ).order_by("-last_seen").first()
        
        if history:
            # Update existing record
            history.last_seen = timestamp
            history.sighting_count += 1
            history.save()
        else:
            # Create new history record
            MACAddressHistory.objects.create(
                mac_address=mac,
                device=device,
                interface=interface,
                vlan=vlan,
                entry_type=entry_type,
                first_seen=timestamp,
                last_seen=timestamp,
                sighting_count=1,
            )


register_jobs(MACAddressCollector)
