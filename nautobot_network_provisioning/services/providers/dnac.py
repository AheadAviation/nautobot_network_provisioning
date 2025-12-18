"""Cisco DNA Center (DNAC) provider stub (Phase 6).

This is intentionally a thin skeleton to establish the provider interface and config shape.
"""

from __future__ import annotations

from typing import Any

import requests

from nautobot_network_provisioning.models import ProviderConfig
from nautobot_network_provisioning.services.provider_runtime import ProviderOperationNotSupported, ProviderOperationResult


class DNACProvider:
    """DNAC provider driver (stub)."""

    def __init__(self, *, provider_config: ProviderConfig):
        self.provider_config = provider_config

    def validate_target(self, *, target: Any) -> None:  # noqa: ANN401
        # DNAC targets are typically a Site/Device mapping in DNAC, not necessarily a direct Nautobot Device.
        return None

    def _session(self) -> requests.Session:
        settings = self.provider_config.settings or {}
        base_url = (settings.get("base_url") or "").rstrip("/")
        token = settings.get("token")
        if not base_url or not token:
            raise ValueError("DNAC ProviderConfig.settings must include base_url and token.")
        s = requests.Session()
        s.headers.update({"X-Auth-Token": str(token), "Accept": "application/json"})
        s.base_url = base_url  # type: ignore[attr-defined]
        return s

    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        raise ProviderOperationNotSupported("DNAC diff is not implemented yet (Phase 6 stub).")

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        raise ProviderOperationNotSupported("DNAC apply is not implemented yet (Phase 6 stub).")


