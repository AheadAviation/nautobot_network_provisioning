"""Configuration push service using Nornir and Netmiko."""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from nautobot.dcim.models import Device, Interface

logger = logging.getLogger(__name__)


@dataclass
class ConfigPushResult:
    """Result of a configuration push operation."""
    
    success: bool
    device_name: str
    interface_name: str
    previous_config: str = ""
    applied_config: str = ""
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "device_name": self.device_name,
            "interface_name": self.interface_name,
            "previous_config": self.previous_config,
            "applied_config": self.applied_config,
            "error_message": self.error_message,
        }


def get_device_credentials(device: Device) -> Tuple[str, str, str]:
    """
    Get connection credentials for a device.
    
    Attempts to retrieve credentials from:
    1. Nautobot Secrets integration
    2. Device custom fields
    3. Default credentials from app settings
    
    Args:
        device: Nautobot Device object
        
    Returns:
        Tuple of (username, password, secret/enable_password)
    """
    # Try to get from Nautobot secrets
    try:
        from nautobot.extras.models import SecretsGroup
        if device.secrets_group:
            secrets = device.secrets_group.get_secret_value(
                access_type="generic",
                secret_type="username-password",
            )
            if secrets:
                return (
                    secrets.get("username", ""),
                    secrets.get("password", ""),
                    secrets.get("secret", ""),
                )
    except Exception:
        pass
    
    # Fallback to environment or defaults
    import os
    return (
        os.environ.get("NETACCESS_DEVICE_USERNAME", "admin"),
        os.environ.get("NETACCESS_DEVICE_PASSWORD", ""),
        os.environ.get("NETACCESS_DEVICE_SECRET", ""),
    )


def get_device_platform(device: Device) -> str:
    """
    Get the Nornir/Netmiko platform type for a device.
    
    Args:
        device: Nautobot Device object
        
    Returns:
        Platform string (e.g., 'cisco_ios', 'cisco_nxos')
    """
    if device.platform:
        slug = device.platform.network_driver or device.platform.napalm_driver or ""
        
        # Map common platform names
        platform_map = {
            "cisco_ios": "cisco_ios",
            "cisco_iosxe": "cisco_ios",
            "cisco_nxos": "cisco_nxos",
            "cisco_nxos_ssh": "cisco_nxos_ssh",
            "cisco_iosxr": "cisco_xr",
            "arista_eos": "arista_eos",
            "juniper_junos": "juniper_junos",
        }
        
        return platform_map.get(slug.lower(), slug.lower())
    
    return "cisco_ios"  # Default fallback


def get_interface_running_config(
    device: Device,
    interface: Interface,
) -> Tuple[bool, str]:
    """
    Get the current running configuration for an interface.
    
    Args:
        device: Nautobot Device object
        interface: Nautobot Interface object
        
    Returns:
        Tuple of (success, config_text_or_error)
    """
    try:
        from netmiko import ConnectHandler
        
        username, password, secret = get_device_credentials(device)
        platform = get_device_platform(device)
        
        # Get device IP
        if device.primary_ip4:
            host = str(device.primary_ip4.host)
        elif device.primary_ip6:
            host = str(device.primary_ip6.host)
        else:
            return False, f"No IP address configured for device {device.name}"
        
        connection_params = {
            "device_type": platform,
            "host": host,
            "username": username,
            "password": password,
            "secret": secret,
            "timeout": 30,
        }
        
        with ConnectHandler(**connection_params) as conn:
            if secret:
                conn.enable()
            
            command = f"show running-config interface {interface.name}"
            output = conn.send_command(command)
            
            return True, output
            
    except Exception as e:
        logger.error(f"Failed to get running config: {e}")
        return False, str(e)


def push_interface_config(
    device: Device,
    interface: Interface,
    config_lines: str,
    default_interface: bool = True,
    write_mem: bool = True,
) -> ConfigPushResult:
    """
    Push configuration to a device interface.
    
    Args:
        device: Nautobot Device object
        interface: Nautobot Interface object
        config_lines: Configuration lines to apply (can be semicolon-separated)
        default_interface: Whether to default the interface first
        write_mem: Whether to save configuration after applying
        
    Returns:
        ConfigPushResult with success status and details
    """
    result = ConfigPushResult(
        success=False,
        device_name=device.name,
        interface_name=interface.name,
    )
    
    try:
        from netmiko import ConnectHandler
        
        username, password, secret = get_device_credentials(device)
        platform = get_device_platform(device)
        
        # Get device IP
        if device.primary_ip4:
            host = str(device.primary_ip4.host)
        elif device.primary_ip6:
            host = str(device.primary_ip6.host)
        else:
            result.error_message = f"No IP address configured for device {device.name}"
            return result
        
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
            
            # Get current interface config for backup
            show_cmd = f"show running-config interface {interface.name}"
            result.previous_config = conn.send_command(show_cmd)
            
            # Build configuration commands
            commands = []
            
            # Check for NODEF flag to skip defaulting interface
            if default_interface and "NODEF" not in config_lines:
                commands.append(f"default interface {interface.name}")
            
            # Add interface command
            commands.append(f"interface {interface.name}")
            
            # Parse config lines (semicolon or newline separated)
            for line in config_lines.replace(";", "\n").split("\n"):
                line = line.strip()
                if line and not line.startswith("NODEF"):
                    commands.append(line)
            
            # Send configuration
            output = conn.send_config_set(commands)
            result.applied_config = "\n".join(commands)
            
            # Check for errors in output
            error_patterns = ["% Invalid", "Error:", "% Incomplete"]
            for pattern in error_patterns:
                if pattern in output:
                    result.error_message = output
                    return result
            
            # Write memory if enabled
            if write_mem:
                conn.save_config()
            
            result.success = True
            logger.info(
                f"Successfully pushed config to {device.name}:{interface.name}"
            )
            
    except ImportError:
        result.error_message = "Netmiko library not installed"
        logger.error(result.error_message)
    except Exception as e:
        result.error_message = str(e)
        logger.error(f"Failed to push config to {device.name}:{interface.name}: {e}")
    
    return result


def test_device_connection(device: Device) -> Tuple[bool, str]:
    """
    Test connectivity to a device.
    
    Args:
        device: Nautobot Device object
        
    Returns:
        Tuple of (success, message)
    """
    try:
        from netmiko import ConnectHandler
        
        username, password, secret = get_device_credentials(device)
        platform = get_device_platform(device)
        
        if device.primary_ip4:
            host = str(device.primary_ip4.host)
        elif device.primary_ip6:
            host = str(device.primary_ip6.host)
        else:
            return False, f"No IP address configured for device {device.name}"
        
        connection_params = {
            "device_type": platform,
            "host": host,
            "username": username,
            "password": password,
            "secret": secret,
            "timeout": 30,
        }
        
        with ConnectHandler(**connection_params) as conn:
            if secret:
                conn.enable()
            
            # Simple connectivity test
            output = conn.send_command("show version", read_timeout=30)
            if output:
                return True, "Connection successful"
            else:
                return False, "No output from device"
                
    except ImportError:
        return False, "Netmiko library not installed"
    except Exception as e:
        return False, str(e)
