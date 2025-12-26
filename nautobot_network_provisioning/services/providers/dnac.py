from __future__ import annotations
from typing import Any
import requests
from ..provider_runtime import BaseProvider, ProviderOperationNotSupported, ProviderOperationResult

class DnacProvider(BaseProvider):
    """DNAC provider driver (stub)."""

    def validate_target(self, *, target: Any) -> None:
        return None

    def _session(self) -> requests.Session:
        settings = self.provider_config.parameters or {}
        base_url = (settings.get("base_url") or "").rstrip("/")
        token = settings.get("token")
        if not base_url or not token:
            raise ValueError("DNAC Provider parameters must include base_url and token.")
        s = requests.Session()
        s.headers.update({"X-Auth-Token": str(token), "Accept": "application/json"})
        s.base_url = base_url
        return s

    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:
        raise ProviderOperationNotSupported("DNAC diff is not implemented yet.")

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:
        raise ProviderOperationNotSupported("DNAC apply is not implemented yet.")

