from __future__ import annotations
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Protocol, Dict, Optional
from ..models import AutomationProvider, AutomationProviderConfig


@dataclass
class ProviderOperationResult:
    """Standardized result of a provider operation."""
    ok: bool
    details: Dict[str, Any] = field(default_factory=dict)
    logs: str = ""
    diff: str = ""


class ProviderError(RuntimeError):
    """Base provider runtime error."""
    pass


class ProviderOperationNotSupported(ProviderError):
    """Provider doesn't implement a requested operation."""
    pass


class ProviderDriver(Protocol):
    """Runtime provider driver interface."""
    def validate_target(self, *, target: Any) -> None: ...
    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult: ...
    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult: ...


class BaseProvider:
    """Base class for all provider drivers."""
    def __init__(self, *, provider_config: AutomationProviderConfig):
        self.provider_config = provider_config

    def validate_target(self, *, target: Any) -> None:
        raise NotImplementedError

    def diff(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:
        raise ProviderOperationNotSupported("Diff not supported.")

    def apply(self, *, target: Any, rendered_content: str, context: dict) -> ProviderOperationResult:
        raise NotImplementedError


def load_provider_driver(provider_config: AutomationProviderConfig) -> ProviderDriver:
    """Instantiate provider driver from AutomationProvider.driver_class."""
    provider = provider_config.provider
    dotted = (provider.driver_class or "").strip()
    if not dotted or "." not in dotted:
        raise ProviderError(f"Provider '{provider.name}' has invalid driver_class.")

    module_path, attr = dotted.rsplit(".", 1)
    mod = import_module(module_path)
    cls = getattr(mod, attr, None)
    if cls is None:
        raise ProviderError(f"Provider driver class '{dotted}' not found.")

    return cls(provider_config=provider_config)


def _score_provider_config(*, provider_config: AutomationProviderConfig, device: Any) -> int:
    """Score matching for a device. Higher score wins."""
    score = 0
    if not device:
        return score

    # Locations
    location = getattr(device, "location", None)
    if provider_config.scope_locations.exists():
        if location and provider_config.scope_locations.filter(pk=location.pk).exists():
            score += 30
        else:
            return -1

    # Tenants
    tenant = getattr(device, "tenant", None)
    if provider_config.scope_tenants.exists():
        if tenant and provider_config.scope_tenants.filter(pk=tenant.pk).exists():
            score += 20
        else:
            return -1

    # Platforms
    platform = getattr(device, "platform", None)
    if platform and provider_config.provider.supported_platforms.exists():
        if provider_config.provider.supported_platforms.filter(pk=platform.pk).exists():
            score += 5

    return score


def select_provider_config(*, device: Any) -> AutomationProviderConfig | None:
    """Select best AutomationProviderConfig for a device."""
    qs = AutomationProviderConfig.objects.filter(enabled=True, provider__enabled=True)
    best: AutomationProviderConfig | None = None
    best_score = -1
    for pc in qs:
        score = _score_provider_config(provider_config=pc, device=device)
        if score > best_score:
            best_score = score
            best = pc
    return best
