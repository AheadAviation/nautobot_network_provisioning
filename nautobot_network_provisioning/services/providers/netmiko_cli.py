"""Netmiko CLI provider (Phase 4).

This provider supports:
- apply: send rendered CLI config as a config set

Diff support is intentionally minimal in v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nautobot_network_provisioning.models import ProviderConfig
from nautobot_network_provisioning.services.provider_runtime import (
    ProviderOperationNotSupported,
    ProviderOperationResult,
)


@dataclass
class NetmikoCredentials:
    host: str
    username: str
    password: str
    device_type: str


def _get_setting(settings: dict, *names: str, default=None):  # noqa: ANN001
    for n in names:
        if n in settings:
            return settings[n]
    return default


class NetmikoCLIProvider:
    """Netmiko provider driver."""

    def __init__(self, *, provider_config: ProviderConfig):
        self.provider_config = provider_config

    def validate_target(self, *, target: Any) -> None:  # noqa: ANN401
        if target is None:
            raise ValueError("Target is required.")
        if not getattr(target, "primary_ip4", None) and not getattr(target, "primary_ip", None) and not getattr(target, "name", None):
            raise ValueError("Target device has no primary IP and no hostname.")

    def _credentials(self, *, target: Any) -> NetmikoCredentials:  # noqa: ANN401
        settings = self.provider_config.settings or {}
        host = None

        primary_ip = getattr(target, "primary_ip4", None) or getattr(target, "primary_ip", None)
        if primary_ip and getattr(primary_ip, "address", None):
            host = str(primary_ip.address).split("/")[0]
        host = host or _get_setting(settings, "host") or getattr(target, "name", None)
        if not host:
            raise ValueError("Unable to determine target host for Netmiko.")

        username = _get_setting(settings, "username", "user")
        password = _get_setting(settings, "password", "pass")
        device_type = _get_setting(settings, "device_type", "netmiko_device_type", default=None)

        # Best-effort guess: allow using platform slug as device_type when configured that way.
        device_type = device_type or getattr(getattr(target, "platform", None), "slug", None)
        if not device_type:
            raise ValueError("Netmiko device_type is required (set in ProviderConfig.settings.device_type).")

        return NetmikoCredentials(host=host, username=str(username), password=str(password), device_type=str(device_type))

    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        raise ProviderOperationNotSupported("NetmikoCLIProvider does not support diff in v1; use Napalm provider for diff.")

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        self.validate_target(target=target)
        creds = self._credentials(target=target)

        from netmiko import ConnectHandler  # imported lazily

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
            except Exception:  # noqa: BLE001
                # Not all platforms support save_config().
                pass
            return ProviderOperationResult(ok=True, details={"applied": len(commands)}, logs="\n".join(logs).strip())
        except Exception as e:  # noqa: BLE001
            return ProviderOperationResult(ok=False, details={"error": str(e)}, logs="\n".join(logs).strip())
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:  # noqa: BLE001
                pass


