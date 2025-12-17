"""ARP Collector job for collecting ARP tables from devices."""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any

from django.db import transaction

from nautobot.apps.jobs import Job, ObjectVar, register_jobs
from nautobot.dcim.models import Device, Interface, Location
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices

from nautobot_network_provisioning.models import MACAddress, ARPEntry, ControlSetting


class ARPCollector(Job):
    """
    Collect ARP tables from network devices.
    
    This job connects to devices and collects their ARP tables,
    creating IP-to-MAC mappings in the database.
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

    class Meta:
        name = "ARP Table Collector"
        description = "Collect ARP tables from network devices"
        has_sensitive_variables = False

    def run(self, device=None, location=None):
        """Execute the ARP table collection."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            # Check if collection is enabled
            if not ControlSetting.is_enabled("mac_collection_enabled", default=True):
                self.logger.info("MAC/ARP collection is disabled")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("Collection is disabled", level_choice=LogLevelChoices.LOG_INFO)
                self.job_result.save()
                return "Collection is disabled"
            
            # Determine which devices to collect from
            devices = self._get_target_devices(device, location)
            
            if not devices:
                self.logger.warning("No devices found to collect from")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("No devices to collect from", level_choice=LogLevelChoices.LOG_WARNING)
                self.job_result.save()
                return "No devices to collect from"
            
            self.logger.info(f"Collecting ARP tables from {len(devices)} devices")
            
            collected_total = 0
            errors = 0
            
            for dev in devices:
                try:
                    count = self._collect_from_device(dev)
                    collected_total += count
                    self.logger.info(f"Collected {count} ARP entries from {dev.name}")
                except Exception as e:
                    errors += 1
                    self.logger.error(f"Failed to collect from {dev.name}: {e}")
            
            summary = f"Collected {collected_total} ARP entries from {len(devices)} devices ({errors} errors)"
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
        
        # Get Layer 3 devices (routers, L3 switches)
        queryset = Device.objects.filter(
            status__name__in=["Active", "Staged"],
        ).exclude(
            platform__isnull=True,
        )
        
        if location:
            queryset = queryset.filter(location=location)
        
        return list(queryset)

    def _collect_from_device(self, device: Device) -> int:
        """Collect ARP table from a single device."""
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
                
                # Get ARP table
                output = conn.send_command("show ip arp")
                
                # Parse and store entries
                entries = self._parse_arp_table(output, device)
                return self._store_arp_entries(entries, device)
                
        except ImportError:
            self.logger.error("Netmiko library not installed")
            return 0
        except Exception as e:
            self.logger.error(f"ARP collection failed for {device.name}: {e}")
            raise

    def _parse_arp_table(self, output: str, device: Device) -> List[Dict[str, Any]]:
        """Parse ARP table output from CLI."""
        entries = []
        
        # Common patterns for Cisco IOS/IOS-XE/NX-OS
        # Format: Protocol  Address          Age (min)  Hardware Addr   Type   Interface
        patterns = [
            # Cisco IOS/IOS-XE
            r"^\s*Internet\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+|-)\s+([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})\s+(\w+)\s+(\S+)",
            # Alternative format with different MAC format
            r"^\s*Internet\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+|-)\s+([0-9a-fA-F:.-]+)\s+(\w+)\s+(\S+)",
        ]
        
        for line in output.split("\n"):
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    ip = match.group(1)
                    mac = self._normalize_mac(match.group(3))
                    entry_type = match.group(4).lower()
                    interface_name = match.group(5)
                    
                    # Skip incomplete entries
                    if "incomplete" in entry_type.lower() or "ffff" in mac.lower():
                        continue
                    
                    entries.append({
                        "ip": ip,
                        "mac": mac,
                        "interface": interface_name,
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
    def _store_arp_entries(self, entries: List[Dict[str, Any]], device: Device) -> int:
        """Store ARP entries in the database."""
        now = datetime.now(timezone.utc)
        stored_count = 0
        
        # Get interface mapping for the device
        interface_map = {
            iface.name: iface
            for iface in Interface.objects.filter(device=device)
        }
        
        for entry in entries:
            ip = entry["ip"]
            mac_str = entry["mac"]
            interface_name = entry.get("interface", "")
            entry_type = entry.get("entry_type", "dynamic")
            
            # Find the interface
            interface = interface_map.get(interface_name)
            if not interface:
                # Try partial match for interface names
                for iface_name, iface in interface_map.items():
                    if interface_name in iface_name or iface_name in interface_name:
                        interface = iface
                        break
            
            # Get or create MAC address record
            mac_obj, created = MACAddress.objects.get_or_create(
                address=mac_str,
                defaults={
                    "mac_type": MACAddress.MACTypeChoices.UNKNOWN,
                    "first_seen": now,
                }
            )
            
            # Update MAC with IP info
            mac_obj.last_ip = ip
            mac_obj.last_seen = now
            if not mac_obj.first_seen:
                mac_obj.first_seen = now
            mac_obj.save()
            
            # Create or update ARP entry
            ARPEntry.objects.update_or_create(
                ip_address=ip,
                device=device,
                vrf="default",
                defaults={
                    "mac_address": mac_obj,
                    "interface": interface,
                    "entry_type": entry_type,
                }
            )
            
            stored_count += 1
        
        return stored_count


register_jobs(ARPCollector)
