"""NAPALM-based CLI provider (Phase 4).

Supports:
- diff: load merge candidate and return device diff
- apply: commit merge candidate

Configuration:
- Prefer Nautobot-native device connectivity where available (Device.get_napalm_device()).
- Fallback to ProviderConfig.settings for driver/credentials if needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nautobot_network_provisioning.models import ProviderConfig
from nautobot_network_provisioning.services.provider_runtime import ProviderOperationResult


@dataclass
class NapalmCredentials:
    hostname: str
    username: str
    password: str
    driver: str
    optional_args: dict[str, Any]


def _guess_napalm_driver_from_platform(platform_slug: str | None) -> str | None:
    if not platform_slug:
        return None
    slug = platform_slug.lower()
    mapping = {
        "ios": "ios",
        "iosxe": "ios",
        "cisco_iosxe": "ios",
        "eos": "eos",
        "arista_eos": "eos",
        "junos": "junos",
        "nxos": "nxos",
    }
    return mapping.get(slug)


def _get_setting(settings: dict, *names: str, default=None):  # noqa: ANN001
    for n in names:
        if n in settings:
            return settings[n]
    return default


def _get_credentials(provider_config: ProviderConfig, *, target: Any) -> NapalmCredentials:  # noqa: ANN401
    settings = provider_config.settings or {}

    primary_ip = getattr(target, "primary_ip4", None) or getattr(target, "primary_ip", None)
    hostname = None
    if primary_ip and getattr(primary_ip, "address", None):
        hostname = str(primary_ip.address).split("/")[0]
    hostname = hostname or _get_setting(settings, "host") or getattr(target, "name", None)
    if not hostname:
        raise ValueError("Unable to determine target hostname/IP for NAPALM.")

    username = _get_setting(settings, "username", "user")
    password = _get_setting(settings, "password", "pass")

    # Best-effort SecretsGroup support (API differs across Nautobot versions).
    sg = provider_config.secrets_group
    if sg:
        for method_name in ("get_secret_value", "get_secret"):
            method = getattr(sg, method_name, None)
            if not callable(method):
                continue
            try:
                # Try common calling conventions.
                username = method(secret_type="username") or username
            except TypeError:
                try:
                    username = method("username") or username
                except Exception:  # noqa: BLE001
                    pass
            except Exception:  # noqa: BLE001
                pass
            try:
                password = method(secret_type="password") or password
            except TypeError:
                try:
                    password = method("password") or password
                except Exception:  # noqa: BLE001
                    pass
            except Exception:  # noqa: BLE001
                pass

    napalm_driver = _get_setting(settings, "napalm_driver", "driver")
    napalm_driver = napalm_driver or _guess_napalm_driver_from_platform(getattr(getattr(target, "platform", None), "slug", None))
    if not napalm_driver:
        raise ValueError("NAPALM driver required (set ProviderConfig.settings.napalm_driver).")

    optional_args = _get_setting(settings, "optional_args", default={}) or {}

    return NapalmCredentials(
        hostname=str(hostname),
        username=str(username),
        password=str(password),
        driver=str(napalm_driver),
        optional_args=dict(optional_args),
    )


class NapalmCLIProvider:
    """NAPALM provider driver."""

    def __init__(self, *, provider_config: ProviderConfig):
        self.provider_config = provider_config

    def validate_target(self, *, target: Any) -> None:  # noqa: ANN401
        if target is None:
            raise ValueError("Target is required.")

    def diff(self, *, target: Any, rendered_content: str, context: dict[str, Any]) -> ProviderOperationResult:  # noqa: ANN401
        self.validate_target(target=target)
        device = None
        # Prefer Nautobot-native napalm device when available.
        get_napalm = getattr(target, "get_napalm_device", None)
        if callable(get_napalm):
            try:
                device = get_napalm()
            except TypeError:
                # Some versions require kwargs; ignore and fall back.
                device = None
        if device is None:
            creds = _get_credentials(self.provider_config, target=target)
            from napalm import get_network_driver  # imported lazily

            driver = get_network_driver(creds.driver)
            device = driver(
                hostname=creds.hostname,
                username=creds.username,
                password=creds.password,
                optional_args=creds.optional_args,
            )
        try:
            device.open()
            device.load_merge_candidate(config=rendered_content or "")
            diff = device.compare_config() or ""
            device.discard_config()
            return ProviderOperationResult(ok=True, details={"diff": diff}, logs="NAPALM compare_config() complete.")
        except Exception as e:  # noqa: BLE001
            try:
                device.discard_config()
            except Exception:  # noqa: BLE001
                pass
            return ProviderOperationResult(ok=False, details={"error": str(e)}, logs="NAPALM diff failed.")
        finally:
            try:
                device.close()
            except Exception:  # noqa: BLE001
                pass

    def apply(self, *, target: Any, rendered_content: str, context: dict[str, Any]) -> ProviderOperationResult:  # noqa: ANN401
        self.validate_target(target=target)
        device = None
        get_napalm = getattr(target, "get_napalm_device", None)
        if callable(get_napalm):
            try:
                device = get_napalm()
            except TypeError:
                device = None
        if device is None:
            creds = _get_credentials(self.provider_config, target=target)
            from napalm import get_network_driver  # imported lazily

            driver = get_network_driver(creds.driver)
            device = driver(
                hostname=creds.hostname,
                username=creds.username,
                password=creds.password,
                optional_args=creds.optional_args,
            )
        try:
            device.open()
            device.load_merge_candidate(config=rendered_content or "")
            diff = device.compare_config() or ""
            device.commit_config()
            return ProviderOperationResult(ok=True, details={"diff": diff, "committed": True}, logs="NAPALM commit_config() complete.")
        except Exception as e:  # noqa: BLE001
            try:
                device.discard_config()
            except Exception:  # noqa: BLE001
                pass
            return ProviderOperationResult(ok=False, details={"error": str(e), "committed": False}, logs="NAPALM apply failed.")
        finally:
            try:
                device.close()
            except Exception:  # noqa: BLE001
                pass


