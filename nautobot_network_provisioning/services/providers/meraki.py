"""Meraki provider stub (Phase 6)."""

from __future__ import annotations

from typing import Any

import requests

from nautobot_network_provisioning.models import ProviderConfig
from nautobot_network_provisioning.services.provider_runtime import ProviderOperationNotSupported, ProviderOperationResult


class MerakiProvider:
    """Meraki Dashboard API provider driver (stub)."""

    def __init__(self, *, provider_config: ProviderConfig):
        self.provider_config = provider_config

    def validate_target(self, *, target: Any) -> None:  # noqa: ANN401
        return None

    def _session(self) -> requests.Session:
        settings = self.provider_config.settings or {}
        base_url = (settings.get("base_url") or "https://api.meraki.com/api/v1").rstrip("/")
        api_key = settings.get("api_key")
        if not api_key:
            raise ValueError("Meraki ProviderConfig.settings must include api_key.")
        s = requests.Session()
        s.headers.update({"X-Cisco-Meraki-API-Key": str(api_key), "Accept": "application/json"})
        s.base_url = base_url  # type: ignore[attr-defined]
        return s

    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        raise ProviderOperationNotSupported("Meraki diff is not implemented yet (Phase 6 stub).")

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        raise ProviderOperationNotSupported("Meraki apply is not implemented yet (Phase 6 stub).")


