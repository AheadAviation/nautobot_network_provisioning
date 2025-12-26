"""
Context Resolver Service (v2.0)

Implements the "Secret Sauce" Variable Resolution Engine.
Hierarchy (Highest to Lowest):
1. Runtime Form Inputs / Studio Overrides
2. Local Context (device.local_context_data)
3. Config Context (device.config_context)
4. Native Model Attributes (device.hostname, etc.)
5. Task Defaults
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from nautobot.dcim.models import Device

logger = logging.getLogger(__name__)

def get_nested_value(obj: Any, path: str, default: Any = None) -> Any:
    """Traverse a nested dict/object by dot-separated path."""
    if not path: return default
    keys = path.split(".")
    current = obj
    for key in keys:
        if current is None: return default
        if isinstance(current, dict):
            current = current.get(key, None)
        elif hasattr(current, key):
            current = getattr(current, key, None)
            if callable(current) and not isinstance(current, type):
                try: current = current()
                except Exception: current = None
        else: return default
    return current if current is not None else default

def serialize_value(value: Any) -> Any:
    """Safely serialize values for JSON context."""
    if value is None: return None
    if hasattr(value, 'all'): # QuerySet
        return [serialize_value(item) for item in value.all()]
    if hasattr(value, 'pk'): # Model Instance
        return {"id": str(value.pk), "display": str(value), "slug": getattr(value, 'slug', None)}
    if hasattr(value, 'ip'): return str(value) # IP Address
    if isinstance(value, (str, int, float, bool, list, dict)): return value
    return str(value)

class ContextResolver:
    """
    The core engine that resolves the 'Intent Context' for a Task.
    """
    
    ALLOWED_MODEL_ATTRS = [
        "name", "primary_ip4", "primary_ip", "platform", "role", 
        "device_type", "location", "site", "tenant", "serial", "status"
    ]

    def __init__(self, device: Device, overrides: Optional[Dict[str, Any]] = None):
        self.device = device
        self.overrides = overrides or {}
        self._config_context = None
        self._local_context = None

    @property
    def config_context(self) -> Dict[str, Any]:
        if self._config_context is None:
            self._config_context = getattr(self.device, 'config_context', {}) or {}
        return self._config_context

    @property
    def local_context_data(self) -> Dict[str, Any]:
        if self._local_context is None:
            self._local_context = getattr(self.device, 'local_context_data', {}) or {}
        return self._local_context

    def get_native_attributes(self) -> Dict[str, Any]:
        """Expose a subset of safe device attributes."""
        attrs = {}
        for attr in self.ALLOWED_MODEL_ATTRS:
            val = getattr(self.device, attr, None)
            attrs[attr] = serialize_value(val)
        return attrs

    def resolve(self, variable_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds the unified variable tree based on v2.0 hierarchy.
        variable_mappings: list of {name, type, source_binding: {type, path}, default}
        
        Supports both old format (path) and new format (source_binding).
        """
        intended = {}
        provenance = {}

        for mapping in variable_mappings:
            name = mapping.get("name")
            if not name: continue
            
            # Support new source_binding format
            source_binding = mapping.get("source_binding", {})
            if source_binding:
                binding_type = source_binding.get("type", "user_input")
                path = source_binding.get("path", "")
            else:
                # Legacy format: direct path
                path = mapping.get("path", "")
                # Infer binding type from path (backward compatibility)
                binding_type = "user_input"  # Default if no path
            
            val = None
            source = None

            # 1. Studio Overrides / Runtime Inputs (always highest priority)
            if name in self.overrides:
                val = self.overrides[name]
                source = "override"

            # 2. Resolve based on source_binding type
            if val is None:
                if binding_type == "user_input":
                    # User input - will be provided at runtime, use default if available
                    pass
                elif binding_type == "local_context" and path:
                    val = get_nested_value(self.local_context_data, path)
                    if val is not None: source = "local_context"
                elif binding_type == "config_context" and path:
                    val = get_nested_value(self.config_context, path)
                    if val is not None: source = "config_context"
                elif binding_type == "device_attr" and path:
                    native_val = get_nested_value(self.device, path)
                    if native_val is not None:
                        val = serialize_value(native_val)
                        source = "model_attribute"
                
                # Fallback: try all sources if binding_type not specified (legacy behavior)
                if val is None and path and not source_binding:
                    # Try local context
                    val = get_nested_value(self.local_context_data, path)
                    if val is not None: source = "local_context"
                    # Try config context
                    if val is None:
                        val = get_nested_value(self.config_context, path)
                        if val is not None: source = "config_context"
                    # Try device attributes
                    if val is None:
                        native_val = get_nested_value(self.device, path)
                        if native_val is not None:
                            val = serialize_value(native_val)
                            source = "model_attribute"

            # 3. Task Defaults (lowest priority)
            if val is None:
                val = mapping.get("default")
                if val is not None: source = "default"

            intended[name] = val
            provenance[name] = source

        return {
            "device": self.get_native_attributes(),
            "intended": intended,
            "provenance": provenance,
            "config_context": self.config_context,
            "local_context": self.local_context_data
        }
