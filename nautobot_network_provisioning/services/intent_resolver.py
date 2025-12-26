from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from django.contrib.contenttypes.models import ContentType
from nautobot.dcim.models import Device, Interface
from nautobot.core.models.generics import PrimaryModel

logger = logging.getLogger(__name__)

class IntentResolver:
    """
    Resolves the 'Hierarchy of Intent' for a given object.
    
    1. Core Data Models (e.g. Interface model attributes)
    2. Config Context (Global/Scoped JSON)
    3. Local Context (Device-specific JSON)
    4. Request Inputs (Transient/Override data)
    """

    def resolve_intent(
        self, 
        obj: PrimaryModel, 
        request_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for intent resolution.
        """
        if isinstance(obj, Device):
            return self._resolve_device_intent(obj, request_inputs)
        elif isinstance(obj, Interface):
            return self._resolve_interface_intent(obj, request_inputs)
        
        # Fallback for other models
        return self._resolve_generic_intent(obj, request_inputs)

    def _resolve_device_intent(self, device: Device, inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        intent = {
            "hostname": device.name,
            "platform": device.platform.slug if device.platform else None,
            "site": device.site.slug if device.site else None,
            # Add other core model fields as needed
        }

        # Merge Config Context
        config_context = device.get_config_context()
        intent.update(config_context)

        # Merge Local Context (Nautobot 2.x stores this in local_config_context_data or similar)
        if hasattr(device, "local_config_context_data") and device.local_config_context_data:
            intent.update(device.local_config_context_data)

        # Merge Request Inputs
        if inputs:
            intent.update(inputs)

        return intent

    def _resolve_interface_intent(self, interface: Interface, inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # Start with core model data
        intent = {
            "name": interface.name,
            "description": interface.description,
            "enabled": interface.enabled,
            "mode": interface.mode,
            "untagged_vlan": interface.untagged_vlan.vid if interface.untagged_vlan else None,
            "tagged_vlans": [v.vid for v in interface.tagged_vlans.all()] if interface.mode == "tagged" else [],
        }

        # Interfaces don't have their own config context, but they might have data in the Device context
        # We look for a key matching the interface name in the resolved device intent
        device_intent = self._resolve_device_intent(interface.device, None)
        interface_data = device_intent.get("interfaces", {}).get(interface.name, {})
        intent.update(interface_data)

        # Merge Request Inputs
        if inputs:
            intent.update(inputs)

        return intent

    def _resolve_generic_intent(self, obj: PrimaryModel, inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        intent = {}
        # Basic serialization of core model fields
        for field in obj._meta.fields:
            if not field.is_relation:
                intent[field.name] = getattr(obj, field.name)
        
        if inputs:
            intent.update(inputs)
            
        return intent

