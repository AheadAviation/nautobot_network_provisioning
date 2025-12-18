"""ServiceNow provider stub (Phase 6)."""

from __future__ import annotations

from typing import Any

import requests

from nautobot_network_provisioning.models import ProviderConfig
from nautobot_network_provisioning.services.provider_runtime import ProviderOperationNotSupported, ProviderOperationResult


class ServiceNowProvider:
    """ServiceNow provider driver (stub)."""

    def __init__(self, *, provider_config: ProviderConfig):
        self.provider_config = provider_config

    def validate_target(self, *, target: Any) -> None:  # noqa: ANN401
        # ITSM targets are typically tickets/requests, not network devices.
        return None

    def _session(self) -> requests.Session:
        settings = self.provider_config.settings or {}
        instance_url = (settings.get("instance_url") or "").rstrip("/")
        username = settings.get("username")
        password = settings.get("password")
        if not instance_url or not username or not password:
            raise ValueError("ServiceNow ProviderConfig.settings must include instance_url, username, password.")
        s = requests.Session()
        s.auth = (str(username), str(password))
        s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        s.base_url = instance_url  # type: ignore[attr-defined]
        return s

    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        raise ProviderOperationNotSupported("ServiceNow diff is not implemented yet (Phase 6 stub).")

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:  # noqa: ANN401
        raise ProviderOperationNotSupported("ServiceNow apply is not implemented yet (Phase 6 stub).")


