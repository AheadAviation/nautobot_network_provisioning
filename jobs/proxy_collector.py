"""
Proxy-based data collection jobs.

These jobs use the remote proxy Celery worker to collect data from
devices that are not directly accessible from Nautobot.
"""

import logging
from datetime import datetime, timezone

from django.db import transaction

from nautobot.apps.jobs import Job, register_jobs, BooleanVar, MultiObjectVar, ObjectVar
from nautobot.dcim.models import Device
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices

from nautobot_network_provisioning.services.proxy_worker import (
    get_proxy_client,
    proxy_execute_command,
    proxy_get_mac_table,
    proxy_get_arp_table,
    proxy_ping,
    test_proxy_connection,
)


class ProxyConnectionTest(Job):
    """
    Test connectivity to the proxy Celery worker.
    
    This job verifies that Nautobot can communicate with the remote
    proxy worker that has access to the device network.
    """
    
    name = "Proxy Worker Connection Test"
    description = "Test connectivity to the remote proxy Celery worker"
    
    class Meta:
        name = "Proxy Worker Connection Test"
        description = "Test connectivity to the remote proxy Celery worker"
        has_sensitive_variables = False
    
    def run(self, **kwargs):
        """Execute the connection test."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            self.logger.info("Testing proxy worker connection...")
            
            # Check if proxy client is available
            client = get_proxy_client()
            
            if not client.config.enabled:
                self.logger.error("Proxy worker is disabled in configuration")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log("Proxy worker is disabled", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return "FAILED: Proxy worker disabled"
            
            self.logger.info(f"Proxy broker URL: {client.config.broker_url}")
            self.logger.info(f"Proxy queue: {client.config.queue_name}")
            
            # Test the connection
            success, message = test_proxy_connection()
            
            if success:
                self.logger.info(f"✅ {message}")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log(message, level_choice=LogLevelChoices.LOG_INFO)
                self.job_result.save()
                return f"SUCCESS: {message}"
            else:
                self.logger.error(f"❌ {message}")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log(message, level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return f"FAILED: {message}"

        except Exception as e:
            error_message = f"Job failed with error: {str(e)}"
            self.logger.error(error_message)
            self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
            self.job_result.log(error_message, level_choice=LogLevelChoices.LOG_ERROR)
            self.job_result.save()
            raise


class ProxyMACCollector(Job):
    """
    Collect MAC address tables from devices via the proxy worker.
    
    This job sends tasks to the remote proxy worker which has network
    access to the devices, collects the MAC tables, and stores them
    in Nautobot.
    """
    
    name = "Proxy MAC Collector"
    description = "Collect MAC address tables from devices via proxy worker"
    
    devices = MultiObjectVar(
        model=Device,
        required=False,
        description="Specific devices to collect from (leave empty for all active devices)",
    )
    dry_run = BooleanVar(
        default=True,
        description="If checked, only show what would be collected without saving",
    )
    
    class Meta:
        name = "Proxy MAC Collector"
        description = "Collect MAC address tables from devices via proxy worker"
        has_sensitive_variables = True  # We handle credentials
    
    def _get_device_credentials(self, device: Device) -> tuple:
        """Get credentials for a device."""
        # Try to get from secrets first
        try:
            from nautobot.extras.models import SecretsGroup
            
            secrets_group = device.secrets_group
            if secrets_group:
                username = secrets_group.get_secret_value(
                    access_type="Generic",
                    secret_type="username",
                )
                password = secrets_group.get_secret_value(
                    access_type="Generic", 
                    secret_type="password",
                )
                return username, password
        except Exception:
            pass
        
        # Fall back to environment variables
        import os
        return (
            os.getenv("NAPALM_USERNAME", "admin"),
            os.getenv("NAPALM_PASSWORD", "admin"),
        )
    
    def _get_device_type(self, device: Device) -> str:
        """Map Nautobot platform to Netmiko device type."""
        platform_mapping = {
            "cisco_ios": "cisco_ios",
            "cisco_nxos": "cisco_nxos",
            "cisco_xe": "cisco_xe",
            "cisco_xr": "cisco_xr",
            "arista_eos": "arista_eos",
            "juniper_junos": "juniper_junos",
            "dell_sonic": "dell_sonic",
            "dell_os10": "dell_os10",
        }
        
        if device.platform:
            platform_slug = device.platform.network_driver or device.platform.name.lower()
            return platform_mapping.get(platform_slug, "cisco_ios")
        
        return "cisco_ios"
    
    def run(self, devices=None, dry_run=True, **kwargs):
        """Execute the MAC collection job."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            # Test proxy connection first
            client = get_proxy_client()
            if not client.is_available:
                self.logger.error("Proxy worker is not available")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log("Proxy worker is not available", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return "FAILED: Proxy worker not available"
            
            # Get devices to collect from
            if devices:
                target_devices = list(devices)
            else:
                # Get all active devices with a primary IP
                target_devices = Device.objects.filter(
                    status__name="Active",
                    primary_ip4__isnull=False,
                ).select_related("platform", "device_type__manufacturer")[:50]  # Limit for safety
            
            self.logger.info(f"Collecting MAC tables from {len(target_devices)} devices")
            
            success_count = 0
            failed_count = 0
            
            for device in target_devices:
                if not device.primary_ip4:
                    self.logger.warning(f"Skipping {device.name}: No primary IP")
                    continue
                
                host = str(device.primary_ip4.address.ip)
                username, password = self._get_device_credentials(device)
                device_type = self._get_device_type(device)
                
                self.logger.info(f"Collecting from {device.name} ({host}) via proxy...")
                
                try:
                    if dry_run:
                        self.logger.info(f"  [DRY RUN] Would collect MAC table from {device.name}")
                        success_count += 1
                    else:
                        result = proxy_get_mac_table(
                            host=host,
                            username=username,
                            password=password,
                            timeout=120,
                        )
                        
                        if result.get("success"):
                            output = result.get("output", "")
                            mac_count = output.count(":")  # Rough estimate
                            self.logger.info(f"  ✅ Collected MAC table ({mac_count} approximate entries)")
                            success_count += 1
                            
                            # TODO: Parse and store MAC entries
                            # self._process_mac_output(device, output)
                        else:
                            self.logger.error(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                            failed_count += 1
                            
                except TimeoutError:
                    self.logger.error(f"  ❌ Timeout collecting from {device.name}")
                    failed_count += 1
                except Exception as e:
                    self.logger.error(f"  ❌ Error: {str(e)}")
                    failed_count += 1
            
            summary = f"Completed: {success_count} successful, {failed_count} failed"
            self.logger.info(summary)
            
            # Mark job as SUCCESS (even with partial failures - it completed its work)
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


class ProxyDeviceCommand(Job):
    """
    Execute a command on a device via the proxy worker.
    
    Useful for ad-hoc commands or troubleshooting.
    """
    
    name = "Proxy Device Command"
    description = "Execute a command on a device via proxy worker"
    
    device = ObjectVar(
        model=Device,
        required=True,
        description="Device to execute command on",
    )
    command = BooleanVar(
        default=False,
        description="Command is a config command (vs show command)",
    )
    
    class Meta:
        name = "Proxy Device Command"
        description = "Execute a command on a device via proxy worker"
        has_sensitive_variables = True
    
    def run(self, device, command="show version", **kwargs):
        """Execute a command on the device."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            client = get_proxy_client()
            if not client.is_available:
                self.logger.error("Proxy worker is not available")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log("Proxy worker is not available", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return "FAILED: Proxy worker not available"
            
            if not device.primary_ip4:
                self.logger.error(f"Device {device.name} has no primary IP")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log("Device has no primary IP", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return "FAILED: No primary IP"
            
            host = str(device.primary_ip4.address.ip)
            
            # Get credentials (simplified - you'd normally use secrets)
            import os
            username = os.getenv("NAPALM_USERNAME", "admin")
            password = os.getenv("NAPALM_PASSWORD", "admin")
            
            self.logger.info(f"Executing '{command}' on {device.name} ({host}) via proxy...")
            
            result = proxy_execute_command(
                host=host,
                username=username,
                password=password,
                command=command,
                device_type="cisco_ios",
                timeout=120,
            )
            
            if result.get("success"):
                output = result.get("output", "")
                self.logger.info(f"Command output:\n{output}")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("Command executed successfully", level_choice=LogLevelChoices.LOG_INFO)
                self.job_result.save()
                return output
            else:
                error = result.get("error", "Unknown error")
                self.logger.error(f"Command failed: {error}")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log(f"Command failed: {error}", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return f"FAILED: {error}"

        except Exception as e:
            error_message = f"Job failed with error: {str(e)}"
            self.logger.error(error_message)
            self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
            self.job_result.log(error_message, level_choice=LogLevelChoices.LOG_ERROR)
            self.job_result.save()
            raise


# Register jobs
register_jobs(ProxyConnectionTest, ProxyMACCollector, ProxyDeviceCommand)
