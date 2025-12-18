"""Template rendering for the provisioning platform.

This module intentionally implements **Jinja2-only** rendering and a standardized
context schema as described in `docs/design.md`.

Standard top-level context keys:
- device
- interfaces
- intended
- facts
- meta
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_context(
    *,
    device: Any = None,
    interfaces: Any = None,
    intended: Optional[Dict[str, Any]] = None,
    facts: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a standardized context dict for rendering.

    Notes:
    - We intentionally do **not** flatten objects into strings; Jinja templates should be able
      to access nested dicts and object attributes.
    """

    ctx: Dict[str, Any] = {
        "device": device,
        "interfaces": interfaces,
        "intended": intended or {},
        "facts": facts or {},
        "meta": {"timestamp": _utc_iso(), **(meta or {})},
    }

    # Convenience: if interfaces not provided, derive from device when possible.
    if ctx["interfaces"] is None and device is not None:
        if hasattr(device, "interfaces"):
            ctx["interfaces"] = device.interfaces.all() if hasattr(device.interfaces, "all") else device.interfaces

    if extra:
        ctx.update(extra)
    return ctx


def render_jinja2_template(template_text: str, context: Dict[str, Any]) -> str:
    """Render template text using Jinja2 with StrictUndefined (fail fast)."""

    from jinja2 import Environment, StrictUndefined

    env = Environment(
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.from_string(template_text or "")
    return template.render(**(context or {}))


def render_template_from_context(template_text: str, context: Dict[str, Any]) -> str:
    """Render with a pre-built context dict."""

    return render_jinja2_template(template_text, context or {})


def render_template(
    *,
    template_text: str,
    device: Any = None,
    interfaces: Any = None,
    intended: Optional[Dict[str, Any]] = None,
    facts: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Convenience wrapper to build the standard context and render."""

    return render_template_from_context(
        template_text,
        build_context(device=device, interfaces=interfaces, intended=intended, facts=facts, meta=meta, extra=extra),
    )


