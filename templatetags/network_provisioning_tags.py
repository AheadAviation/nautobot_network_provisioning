"""Custom template tags for NetAccess app."""

from django import template

register = template.Library()


@register.filter
def format_mac(mac_address):
    """
    Format a MAC address string consistently.
    
    Usage: {{ mac_string|format_mac }}
    """
    if not mac_address:
        return ""
    
    # Remove all separators
    mac_clean = mac_address.replace(":", "").replace("-", "").replace(".", "").upper()
    
    if len(mac_clean) != 12:
        return mac_address
    
    # Format as XX:XX:XX:XX:XX:XX
    return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))


@register.filter
def mac_vendor_prefix(mac_address):
    """
    Extract the vendor prefix (first 3 octets) from a MAC address.
    
    Usage: {{ mac_string|mac_vendor_prefix }}
    """
    if not mac_address:
        return ""
    
    # Remove all separators
    mac_clean = mac_address.replace(":", "").replace("-", "").replace(".", "").upper()
    
    if len(mac_clean) < 6:
        return ""
    
    # Return first 3 octets
    return ":".join(mac_clean[i:i+2] for i in range(0, 6, 2))


@register.simple_tag
def work_queue_status_badge(status):
    """
    Return the appropriate Bootstrap badge class for a work queue status.
    
    Usage: {% work_queue_status_badge entry.status %}
    """
    status_classes = {
        "pending": "bg-warning",
        "in_progress": "bg-info",
        "completed": "bg-success",
        "failed": "bg-danger",
        "cancelled": "bg-secondary",
    }
    return status_classes.get(status, "bg-secondary")


@register.simple_tag
def mac_type_badge(mac_type):
    """
    Return the appropriate Bootstrap badge class for a MAC type.
    
    Usage: {% mac_type_badge mac.mac_type %}
    """
    type_classes = {
        "interface": "bg-primary",
        "endpoint": "bg-success",
        "virtual": "bg-info",
        "unknown": "bg-secondary",
    }
    return type_classes.get(mac_type, "bg-secondary")
