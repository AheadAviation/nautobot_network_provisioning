from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from ..provider_runtime import BaseProvider, ProviderOperationResult, ProviderOperationNotSupported

@dataclass
class NetmikoCredentials:
    host: str
    username: str
    password: str
    device_type: str

def _get_setting(settings: dict, *names: str, default=None):
    for n in names:
        if n in settings:
            return settings[n]
    return default

class NetmikoCLIProvider(BaseProvider):
    """Netmiko provider driver."""

    def validate_target(self, *, target: Any) -> None:
        if target is None:
            raise ValueError("Target is required.")
        if not getattr(target, "primary_ip4", None) and not getattr(target, "primary_ip", None) and not getattr(target, "name", None):
            raise ValueError("Target device has no primary IP and no hostname.")

    def _credentials(self, *, target: Any) -> NetmikoCredentials:
        settings = self.provider_config.parameters or {}
        host = None

        primary_ip = getattr(target, "primary_ip4", None) or getattr(target, "primary_ip", None)
        if primary_ip and getattr(primary_ip, "address", None):
            host = str(primary_ip.address).split("/")[0]
        host = host or _get_setting(settings, "host") or getattr(target, "name", None)
        
        username = _get_setting(settings, "username", "user")
        password = _get_setting(settings, "password", "pass")
        device_type = _get_setting(settings, "device_type", "netmiko_device_type", default=None)
        
        device_type = device_type or getattr(getattr(target, "platform", None), "slug", None)
        if not device_type:
            raise ValueError("Netmiko device_type is required.")

        return NetmikoCredentials(host=host, username=str(username), password=str(password), device_type=str(device_type))

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:
        self.validate_target(target=target)
        creds = self._credentials(target=target)

        from netmiko import ConnectHandler
        commands = [line for line in (rendered_content or "").splitlines() if line.strip()]
        
        if not commands:
            return ProviderOperationResult(ok=True, details={"applied": 0}, logs="No commands to apply.")

        logs = []
        conn = None
        try:
            conn = ConnectHandler(
                host=creds.host,
                username=creds.username,
                password=creds.password,
                device_type=creds.device_type,
            )
            out = conn.send_config_set(commands)
            logs.append(out or "")
            try:
                conn.save_config()
            except Exception:
                pass
            return ProviderOperationResult(ok=True, details={"applied": len(commands)}, logs="\n".join(logs).strip())
        except Exception as e:
            return ProviderOperationResult(ok=False, details={"error": str(e)}, logs="\n".join(logs).strip())
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

