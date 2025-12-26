from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from ..provider_runtime import BaseProvider, ProviderOperationResult

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
        "ios": "ios", "iosxe": "ios", "cisco_iosxe": "ios",
        "eos": "eos", "arista_eos": "eos", "junos": "junos", "nxos": "nxos",
    }
    return mapping.get(slug)

def _get_setting(settings: dict, *names: str, default=None):
    for n in names:
        if n in settings:
            return settings[n]
    return default

class NapalmCLIProvider(BaseProvider):
    """NAPALM provider driver."""

    def validate_target(self, *, target: Any) -> None:
        if target is None:
            raise ValueError("Target is required.")

    def _get_credentials(self, *, target: Any) -> NapalmCredentials:
        settings = self.provider_config.parameters or {}
        primary_ip = getattr(target, "primary_ip4", None) or getattr(target, "primary_ip", None)
        hostname = None
        if primary_ip and getattr(primary_ip, "address", None):
            hostname = str(primary_ip.address).split("/")[0]
        hostname = hostname or _get_setting(settings, "host") or getattr(target, "name", None)
        
        username = _get_setting(settings, "username", "user")
        password = _get_setting(settings, "password", "pass")
        
        napalm_driver = _get_setting(settings, "napalm_driver", "driver")
        napalm_driver = napalm_driver or _guess_napalm_driver_from_platform(getattr(getattr(target, "platform", None), "slug", None))
        
        optional_args = _get_setting(settings, "optional_args", default={}) or {}

        return NapalmCredentials(
            hostname=str(hostname),
            username=str(username),
            password=str(password),
            driver=str(napalm_driver),
            optional_args=dict(optional_args),
        )

    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:
        self.validate_target(target=target)
        creds = self._get_credentials(target=target)
        from napalm import get_network_driver
        driver = get_network_driver(creds.driver)
        device = driver(hostname=creds.hostname, username=creds.username, password=creds.password, optional_args=creds.optional_args)
        
        try:
            device.open()
            device.load_merge_candidate(config=rendered_content or "")
            diff = device.compare_config() or ""
            device.discard_config()
            return ProviderOperationResult(ok=True, details={"diff": diff}, logs="NAPALM diff complete.")
        except Exception as e:
            return ProviderOperationResult(ok=False, details={"error": str(e)}, logs="NAPALM diff failed.")
        finally:
            device.close()

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:
        self.validate_target(target=target)
        creds = self._get_credentials(target=target)
        from napalm import get_network_driver
        driver = get_network_driver(creds.driver)
        device = driver(hostname=creds.hostname, username=creds.username, password=creds.password, optional_args=creds.optional_args)
        
        try:
            device.open()
            device.load_merge_candidate(config=rendered_content or "")
            device.commit_config()
            return ProviderOperationResult(ok=True, logs="NAPALM commit complete.")
        except Exception as e:
            return ProviderOperationResult(ok=False, details={"error": str(e)}, logs="NAPALM apply failed.")
        finally:
            device.close()

