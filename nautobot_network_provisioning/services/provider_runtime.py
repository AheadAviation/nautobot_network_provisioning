"""Provider runtime: load/select ProviderConfig and execute diff/apply operations.

Phase 4 (Providers v1).
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol

from nautobot_network_provisioning.models import Provider, ProviderConfig


class ProviderError(RuntimeError):
    """Base provider runtime error."""


class ProviderOperationNotSupported(ProviderError):
    """Provider doesn't implement a requested operation."""


@dataclass(frozen=True)
class ProviderOperationResult:
    """Normalized provider operation result."""

    ok: bool
    details: dict[str, Any]
    logs: str = ""


class ProviderDriver(Protocol):
    """Runtime provider driver interface."""

    def validate_target(self, *, target: Any) -> None:  # noqa: ANN401
        ...

    def diff(self, *, target: Any, rendered_content: str, context: dict[str, Any]) -> ProviderOperationResult:  # noqa: ANN401
        ...

    def apply(self, *, target: Any, rendered_content: str, context: dict[str, Any]) -> ProviderOperationResult:  # noqa: ANN401
        ...


def load_provider_driver(provider_config: ProviderConfig) -> ProviderDriver:
    """Instantiate provider driver from Provider.driver_class."""

    provider: Provider = provider_config.provider
    dotted = (provider.driver_class or "").strip()
    if not dotted or "." not in dotted:
        raise ProviderError(f"Provider '{provider.name}' has invalid driver_class '{provider.driver_class}'.")

    module_path, attr = dotted.rsplit(".", 1)
    mod = import_module(module_path)
    cls = getattr(mod, attr, None)
    if cls is None:
        raise ProviderError(f"Provider driver class '{dotted}' not found.")

    return cls(provider_config=provider_config)  # type: ignore[call-arg]


def _score_provider_config(*, provider_config: ProviderConfig, device: Any) -> int:  # noqa: ANN401
    """Score ProviderConfig match for a given Device.

    Higher score wins. Empty scopes match all (score 0).
    """

    score = 0
    if not device:
        return score

    # Locations (Nautobot 2.3+)
    location = getattr(device, "location", None)
    if provider_config.scope_locations.exists():
        if location and provider_config.scope_locations.filter(pk=getattr(location, "pk", None)).exists():
            score += 30
        else:
            return -1

    # Tenants
    tenant = getattr(device, "tenant", None)
    if provider_config.scope_tenants.exists():
        if tenant and provider_config.scope_tenants.filter(pk=getattr(tenant, "pk", None)).exists():
            score += 20
        else:
            return -1

    # Tags
    if provider_config.scope_tags.exists():
        device_tags = getattr(device, "tags", None)
        if device_tags is None:
            return -1
        if provider_config.scope_tags.filter(pk__in=device_tags.values_list("pk", flat=True)).exists():
            score += 10
        else:
            return -1

    # Platforms (via Provider.supported_platforms)
    platform = getattr(device, "platform", None)
    if platform and provider_config.provider.supported_platforms.exists():
        if provider_config.provider.supported_platforms.filter(pk=getattr(platform, "pk", None)).exists():
            score += 5
        else:
            # Don't hard-fail; let it be eligible if no better match exists.
            score += 0

    return score


def select_provider_config(*, device: Any) -> ProviderConfig | None:  # noqa: ANN401
    """Select best ProviderConfig for a device based on scope matching."""

    qs = ProviderConfig.objects.select_related("provider", "secrets_group").filter(enabled=True, provider__enabled=True)
    best: ProviderConfig | None = None
    best_score = -1
    for pc in qs:
        score = _score_provider_config(provider_config=pc, device=device)
        if score > best_score:
            best_score = score
            best = pc
    return best


