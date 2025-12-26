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
    """
    ctx: Dict[str, Any] = {
        "device": device,
        "interfaces": interfaces,
        "intended": intended or {},
        "facts": facts or {},
        "meta": {"timestamp": _utc_iso(), **(meta or {})},
    }

    # Derive interfaces if not provided
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

