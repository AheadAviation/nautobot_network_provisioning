"""
Template rendering service with TWIX-style variable substitution.

Supports both __VARIABLE__ style (TWIX) and {{ variable }} style (Jinja2).
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional, List

from nautobot.dcim.models import Device, Interface, Location


# Template variable definitions
# Each variable maps to a function that takes a context dict and returns a string
TEMPLATE_VARIABLES: Dict[str, Callable[[Dict[str, Any]], str]] = {
    # Interface variables
    "__INTERFACE__": lambda ctx: ctx.get("interface").name if ctx.get("interface") else ctx.get("interface_name", ""),
    "__SWITCH_PORT__": lambda ctx: ctx.get("interface").name if ctx.get("interface") else ctx.get("switch_port", ""),
    "__PORT__": lambda ctx: ctx.get("interface").name if ctx.get("interface") else ctx.get("interface_name", ""),
    
    # Location variables
    "__BUILDING__": lambda ctx: _get_location_name(ctx.get("building")) or ctx.get("building_name", ""),
    "__COMM_ROOM__": lambda ctx: ctx.get("comm_room") or ctx.get("comm_room_name", ""),
    "__JACK__": lambda ctx: ctx.get("jack") or ctx.get("jack_name", ""),
    
    # Device variables  
    "__SWITCH__": lambda ctx: ctx.get("device").name if ctx.get("device") else ctx.get("device_name", ""),
    "__SWITCH_IP__": lambda ctx: _get_device_ip(ctx.get("device")) or ctx.get("device_ip", ""),
    "__SWITCH_NAME__": lambda ctx: ctx.get("device").name if ctx.get("device") else ctx.get("device_name", ""),
    "__DEVICE__": lambda ctx: ctx.get("device").name if ctx.get("device") else ctx.get("device_name", ""),
    "__DEVICE_NAME__": lambda ctx: ctx.get("device").name if ctx.get("device") else ctx.get("device_name", ""),
    "__DEVICE_IP__": lambda ctx: _get_device_ip(ctx.get("device")) or ctx.get("device_ip", ""),
    "__SWITCH_TYPE__": lambda ctx: _get_device_type(ctx.get("device")) or ctx.get("model", ""),
    "__MODEL__": lambda ctx: _get_device_type(ctx.get("device")) or ctx.get("model", ""),
    "__IOS__": lambda ctx: _get_os_version(ctx.get("device")) or ctx.get("platform", ""),
    "__IOS_VERSION__": lambda ctx: _get_os_version(ctx.get("device")) or ctx.get("platform", ""),
    "__PLATFORM__": lambda ctx: _get_platform_name(ctx.get("device")) or ctx.get("platform", ""),
    
    # Site/Location variables
    "__SITE__": lambda ctx: _get_site_name(ctx.get("device")) or ctx.get("site", ""),
    "__LOCATION__": lambda ctx: _get_site_name(ctx.get("device")) or ctx.get("site", ""),
    "__ROLE__": lambda ctx: _get_role_name(ctx.get("device")) or ctx.get("role", ""),
    
    # User/audit variables
    "__CREATOR__": lambda ctx: ctx.get("requested_by", "") or ctx.get("creator", ""),
    "__USER__": lambda ctx: ctx.get("requested_by", "") or ctx.get("creator", ""),
    "__REQUESTED_BY__": lambda ctx: ctx.get("requested_by", "") or ctx.get("creator", ""),
    
    # Service/Template variables
    "__SERVICE__": lambda ctx: _get_service_name(ctx.get("service")) or ctx.get("service_name", ""),
    "__TEMPLATE__": lambda ctx: _get_service_name(ctx.get("service")) or ctx.get("template_name", ""),
    "__TEMPLATE_NAME__": lambda ctx: ctx.get("template_name", "") or _get_service_name(ctx.get("service")),
    "__VERSION__": lambda ctx: str(ctx.get("template_version", "") or ctx.get("version", "")),
    "__INSTANCE__": lambda ctx: str(ctx.get("template_instance", "") or ctx.get("instance", "")),
    
    # Date/time variables
    "__DATE_APPLIED__": lambda ctx: ctx.get("timestamp") or ctx.get("DATE_APPLIED") or _get_timestamp(),
    "__DATE__": lambda ctx: ctx.get("timestamp") or ctx.get("date_now") or _get_date(),
    "__TIMESTAMP__": lambda ctx: ctx.get("timestamp") or _get_timestamp(),
    "__DATETIME__": lambda ctx: ctx.get("datetime_now") or _get_timestamp(),
    
    # VLAN variable
    "__VLAN__": lambda ctx: str(ctx.get("vlan", "")) if ctx.get("vlan") else "",
}


def _get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get_date() -> str:
    """Get current date."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _get_location_name(location: Optional[Location]) -> str:
    """Get the name from a Location object safely."""
    if location is None:
        return ""
    return location.name if hasattr(location, "name") else str(location)


def _get_device_ip(device: Optional[Device]) -> str:
    """Get the primary IP address from a Device object safely."""
    if device is None:
        return ""
    
    if hasattr(device, "primary_ip4") and device.primary_ip4:
        try:
            return str(device.primary_ip4.host)
        except Exception:
            return str(device.primary_ip4.address).split("/")[0]
    elif hasattr(device, "primary_ip6") and device.primary_ip6:
        try:
            return str(device.primary_ip6.host)
        except Exception:
            return str(device.primary_ip6.address).split("/")[0]
    
    return ""


def _get_device_type(device: Optional[Device]) -> str:
    """Get the device type/model from a Device object safely."""
    if device is None:
        return ""
    
    if hasattr(device, "device_type") and device.device_type:
        return device.device_type.model or ""
    
    return ""


def _get_os_version(device: Optional[Device]) -> str:
    """Get the OS version from a Device object safely."""
    if device is None:
        return ""
    
    # Check common custom field names
    cf_names = ["os_version", "software_version", "ios_version", "version"]
    
    if hasattr(device, "custom_field_data") and device.custom_field_data:
        for cf_name in cf_names:
            value = device.custom_field_data.get(cf_name)
            if value:
                return str(value)
    
    # Fallback to platform name
    return _get_platform_name(device)


def _get_platform_name(device: Optional[Device]) -> str:
    """Get the platform name from a Device object safely."""
    if device is None:
        return ""
    
    if hasattr(device, "platform") and device.platform:
        return device.platform.name or ""
    
    return ""


def _get_site_name(device: Optional[Device]) -> str:
    """Get the site/location name from a Device object safely."""
    if device is None:
        return ""
    
    if hasattr(device, "location") and device.location:
        return device.location.name or ""
    
    return ""


def _get_role_name(device: Optional[Device]) -> str:
    """Get the role name from a Device object safely."""
    if device is None:
        return ""
    
    if hasattr(device, "role") and device.role:
        return device.role.name or ""
    
    return ""


def _get_service_name(service) -> str:
    """Get the service name safely."""
    if service is None:
        return ""
    
    if hasattr(service, "name"):
        return service.name
    
    return str(service)


def build_context(
    device: Device = None,
    interface: Interface = None,
    service = None,
    building: Optional[Location] = None,
    comm_room: str = "",
    jack: str = "",
    requested_by: str = "",
    vlan: Optional[int] = None,
    template_version: Optional[int] = None,
    template_instance: Optional[int] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a context dictionary for template rendering.
    
    Args:
        device: Target Device object
        interface: Target Interface object
        service: Service object
        building: Optional building Location
        comm_room: Optional communications room string
        jack: Optional jack identifier
        requested_by: Username who requested the change
        vlan: Optional VLAN number
        template_version: Template version number
        template_instance: Template instance number
        extra_context: Additional context variables
        
    Returns:
        Context dictionary with all variables
    """
    context: Dict[str, Any] = {
        "device": device,
        "interface": interface,
        "service": service,
        "building": building,
        "comm_room": comm_room,
        "jack": jack,
        "requested_by": requested_by,
        "vlan": vlan,
        "template_version": template_version,
        "template_instance": template_instance,
        "timestamp": _get_timestamp(),
        "date_now": _get_date(),
        "datetime_now": _get_timestamp(),
        "DATE_APPLIED": _get_timestamp(),
    }
    
    # Add device-derived context
    if device:
        context.update({
            "device_name": device.name,
            "device_ip": _get_device_ip(device),
            "model": _get_device_type(device),
            "platform": _get_platform_name(device),
            "site": _get_site_name(device),
            "role": _get_role_name(device),
        })
    
    # Add interface-derived context
    if interface:
        context.update({
            "interface_name": interface.name,
            "switch_port": interface.name,
        })
    
    # Add location-derived context
    if building:
        context["building_name"] = _get_location_name(building)
    
    context["comm_room_name"] = comm_room
    context["jack_name"] = jack
    
    # Add service-derived context
    if service:
        context.update({
            "service_name": _get_service_name(service),
            "template_name": _get_service_name(service),
        })
    
    # Add creator context
    context["creator"] = requested_by
    
    # Add any extra context
    if extra_context:
        context.update(extra_context)
    
    return context


def render_twix_variables(template_text: str, context: Dict[str, Any]) -> str:
    """
    Render template with TWIX-style __VARIABLE__ substitution.
    
    Args:
        template_text: Template text with __VARIABLE__ placeholders
        context: Context dictionary for variable resolution
        
    Returns:
        Rendered template string
    """
    result = template_text
    
    for var_name, var_func in TEMPLATE_VARIABLES.items():
        if var_name in result:
            try:
                value = var_func(context)
                result = result.replace(var_name, str(value) if value else "")
            except Exception:
                # If variable resolution fails, leave placeholder or empty
                pass
    
    return result


def render_jinja2_template(template_text: str, context: Dict[str, Any]) -> str:
    """
    Render template with Jinja2 syntax.
    
    Args:
        template_text: Template text with {{ variable }} syntax
        context: Context dictionary for variable resolution
        
    Returns:
        Rendered template string
    """
    try:
        from jinja2 import Template
    except ImportError:
        raise RuntimeError("Jinja2 not installed. Run: pip install jinja2")
    
    # Build flat context for Jinja2
    flat_context = {}
    
    # Add all simple string values
    for key, value in context.items():
        if isinstance(value, str):
            flat_context[key] = value
        elif value is None:
            flat_context[key] = ""
        elif hasattr(value, "name"):
            flat_context[key] = value.name
        else:
            flat_context[key] = str(value)
    
    # Resolve TWIX variables into flat context
    for var_name, var_func in TEMPLATE_VARIABLES.items():
        # Convert __VARIABLE__ to variable_name for Jinja2
        jinja_name = var_name.strip("_").lower()
        try:
            flat_context[jinja_name] = var_func(context)
        except Exception:
            flat_context[jinja_name] = ""
    
    template = Template(template_text)
    return template.render(**flat_context)


def render_template(
    template_text: str,
    device: Device = None,
    interface: Interface = None,
    service = None,
    building: Optional[Location] = None,
    comm_room: str = "",
    jack: str = "",
    requested_by: str = "",
    vlan: Optional[int] = None,
    template_version: Optional[int] = None,
    template_instance: Optional[int] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Render a configuration template with variable substitution.
    
    Supports both TWIX-style __VARIABLE__ and Jinja2 {{ variable }} syntax.
    First applies TWIX substitution, then Jinja2 if needed.
    
    Args:
        template_text: The template text with variable placeholders
        device: Target Device object
        interface: Target Interface object
        service: Service object
        building: Optional building Location
        comm_room: Optional communications room string
        jack: Optional jack identifier
        requested_by: Username who requested the change
        vlan: Optional VLAN number
        template_version: Template version number
        template_instance: Template instance number
        extra_context: Additional context variables
        
    Returns:
        Rendered template string with all variables replaced
    """
    # Build context dictionary
    context = build_context(
        device=device,
        interface=interface,
        service=service,
        building=building,
        comm_room=comm_room,
        jack=jack,
        requested_by=requested_by,
        vlan=vlan,
        template_version=template_version,
        template_instance=template_instance,
        extra_context=extra_context,
    )
    
    # First apply TWIX-style substitution
    result = render_twix_variables(template_text, context)
    
    # Check if Jinja2 syntax is present
    if "{{" in result or "{%" in result:
        try:
            result = render_jinja2_template(result, context)
        except Exception:
            # If Jinja2 fails, return TWIX-only result
            pass
    
    return result


def render_template_from_context(template_text: str, context: Dict[str, Any]) -> str:
    """
    Render a template using a pre-built context dictionary.
    
    Useful when context is already prepared elsewhere.
    
    Args:
        template_text: Template text with variable placeholders
        context: Pre-built context dictionary
        
    Returns:
        Rendered template string
    """
    # Apply TWIX substitution
    result = render_twix_variables(template_text, context)
    
    # Check if Jinja2 syntax is present
    if "{{" in result or "{%" in result:
        try:
            result = render_jinja2_template(result, context)
        except Exception:
            pass
    
    return result


def get_available_variables() -> Dict[str, str]:
    """
    Get a dictionary of available template variables with descriptions.
    
    Returns:
        Dict mapping variable names to their descriptions
    """
    return {
        # Interface variables
        "__INTERFACE__": "Interface name (e.g., GigabitEthernet1/0/1)",
        "__SWITCH_PORT__": "Same as __INTERFACE__",
        "__PORT__": "Same as __INTERFACE__",
        
        # Location variables
        "__BUILDING__": "Building name",
        "__COMM_ROOM__": "Communications room identifier",
        "__JACK__": "Jack identifier",
        
        # Device variables
        "__SWITCH__": "Switch/device name",
        "__SWITCH_IP__": "Switch primary IP address",
        "__SWITCH_NAME__": "Same as __SWITCH__",
        "__DEVICE__": "Same as __SWITCH__",
        "__DEVICE_NAME__": "Same as __SWITCH__",
        "__DEVICE_IP__": "Same as __SWITCH_IP__",
        "__SWITCH_TYPE__": "Device type/model",
        "__MODEL__": "Same as __SWITCH_TYPE__",
        "__IOS__": "IOS/OS version or platform name",
        "__IOS_VERSION__": "Same as __IOS__",
        "__PLATFORM__": "Platform name",
        
        # Site/Location variables
        "__SITE__": "Site/Location name",
        "__LOCATION__": "Same as __SITE__",
        "__ROLE__": "Device role",
        
        # User/Audit variables
        "__CREATOR__": "Username who requested the change",
        "__USER__": "Same as __CREATOR__",
        "__REQUESTED_BY__": "Same as __CREATOR__",
        
        # Service/Template variables
        "__SERVICE__": "Service/template type name",
        "__TEMPLATE__": "Same as __SERVICE__",
        "__TEMPLATE_NAME__": "Template name",
        "__VERSION__": "Template version number",
        "__INSTANCE__": "Template instance number",
        
        # Date/time variables
        "__DATE_APPLIED__": "Date/time when config is applied",
        "__DATE__": "Current date",
        "__TIMESTAMP__": "Current timestamp",
        "__DATETIME__": "Current date and time",
        
        # Other variables
        "__VLAN__": "VLAN number (if specified)",
    }


def get_variables_help_text() -> str:
    """
    Get formatted help text for template variables.
    
    Returns:
        Multi-line string with variable documentation
    """
    lines = ["Available Template Variables:", "=" * 40, ""]
    
    categories = {
        "Interface": ["__INTERFACE__", "__SWITCH_PORT__", "__PORT__"],
        "Location": ["__BUILDING__", "__COMM_ROOM__", "__JACK__"],
        "Device": ["__SWITCH__", "__SWITCH_IP__", "__SWITCH_TYPE__", "__MODEL__", "__IOS__", "__PLATFORM__"],
        "Site": ["__SITE__", "__LOCATION__", "__ROLE__"],
        "User": ["__CREATOR__", "__USER__", "__REQUESTED_BY__"],
        "Template": ["__SERVICE__", "__TEMPLATE__", "__VERSION__", "__INSTANCE__"],
        "Date/Time": ["__DATE_APPLIED__", "__DATE__", "__TIMESTAMP__", "__DATETIME__"],
        "Other": ["__VLAN__"],
    }
    
    available = get_available_variables()
    
    for category, vars in categories.items():
        lines.append(f"\n{category}:")
        lines.append("-" * len(category))
        for var in vars:
            if var in available:
                lines.append(f"  {var}: {available[var]}")
    
    return "\n".join(lines)


def validate_template(template_text: str) -> Dict[str, Any]:
    """
    Validate a template and identify any unknown variables.
    
    Args:
        template_text: Template text to validate
        
    Returns:
        Dict with 'valid' bool and details about found variables
    """
    # Find all __VARIABLE__ patterns
    pattern = r"__[A-Z_]+__"
    found_vars = set(re.findall(pattern, template_text))
    
    known_vars = set(TEMPLATE_VARIABLES.keys())
    unknown_vars = found_vars - known_vars
    
    # Find Jinja2 variables
    jinja_pattern = r"\{\{\s*(\w+)\s*\}\}"
    jinja_vars = set(re.findall(jinja_pattern, template_text))
    
    return {
        "valid": len(unknown_vars) == 0,
        "found_twix_variables": list(found_vars),
        "unknown_twix_variables": list(unknown_vars),
        "known_twix_variables": list(found_vars & known_vars),
        "jinja2_variables": list(jinja_vars),
        "has_jinja2": bool(jinja_vars) or "{{" in template_text or "{%" in template_text,
    }


def extract_variables(template_text: str) -> List[str]:
    """
    Extract all variable names from a template.
    
    Returns both TWIX-style and Jinja2-style variables.
    
    Args:
        template_text: Template text to analyze
        
    Returns:
        List of variable names found
    """
    variables = []
    
    # Find TWIX variables
    twix_pattern = r"__([A-Z_]+)__"
    for match in re.findall(twix_pattern, template_text):
        variables.append(f"__{match}__")
    
    # Find Jinja2 variables
    jinja_pattern = r"\{\{\s*(\w+)\s*\}\}"
    for match in re.findall(jinja_pattern, template_text):
        variables.append(f"{{{{ {match} }}}}")
    
    return list(set(variables))
