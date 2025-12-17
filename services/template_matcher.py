"""Template matching service for finding the best template for a device.

This service provides both the new Manufacturer/Platform/Version matching
and legacy SwitchProfile pattern matching for backward compatibility.
"""

import fnmatch
import re
from datetime import date
from typing import Optional, List

from django.db.models import Q
from nautobot.dcim.models import Device


def _sql_like_to_regex(pattern: str) -> str:
    """
    Convert SQL LIKE pattern to Python regex.
    
    SQL LIKE:
        % = match any characters (0 or more)
        _ = match exactly one character
        
    Args:
        pattern: SQL LIKE pattern
        
    Returns:
        Regex pattern string
    """
    # Escape regex special characters except % and _
    regex = re.escape(pattern)
    # Convert SQL LIKE wildcards to regex
    regex = regex.replace(r"\%", ".*")
    regex = regex.replace(r"\_", ".")
    # Handle parentheses in patterns like "15.2(%)E%"
    regex = regex.replace(r"\(", r"\(")
    regex = regex.replace(r"\)", r"\)")
    return f"^{regex}$"


def _pattern_match(value: str, pattern: str) -> bool:
    """
    Check if a value matches a SQL LIKE pattern.
    
    Args:
        value: The value to check
        pattern: SQL LIKE pattern (with % and _ wildcards)
        
    Returns:
        True if the value matches the pattern
    """
    if not value or not pattern:
        return False
    
    regex = _sql_like_to_regex(pattern)
    return bool(re.match(regex, value, re.IGNORECASE))


def get_device_model(device: Device) -> str:
    """
    Get the device model string from a Nautobot Device.
    
    Handles various device type naming conventions and normalizes
    for template matching.
    
    Args:
        device: Nautobot Device object
        
    Returns:
        Device model string (e.g., "WS-C3850")
    """
    if not device.device_type:
        return ""
    
    model = device.device_type.model or ""
    
    # Normalize common patterns
    # Handle C9300-48 -> WS-C9300-48 format
    if model.startswith("C9300") and not model.startswith("WS-"):
        model = f"WS-{model}"
    
    # Handle C1-WSC format -> WS-C format
    if model.startswith("C1-WSC"):
        model = f"WS-{model[5:]}"
    
    return model


def get_device_os_version(device: Device) -> str:
    """
    Get the OS version from a Nautobot Device.
    
    Checks custom fields for os_version, software_version, etc.
    
    Args:
        device: Nautobot Device object
        
    Returns:
        OS version string (e.g., "15.2(3)E2")
    """
    # Check common custom field names for OS version
    cf_names = ["os_version", "software_version", "ios_version", "version"]
    
    for cf_name in cf_names:
        if hasattr(device, "custom_field_data") and device.custom_field_data:
            value = device.custom_field_data.get(cf_name)
            if value:
                return str(value)
    
    return ""


def get_device_software_version(device: Device):
    """
    Get the SoftwareVersion object associated with a device.
    
    Uses Nautobot's software version relationship.
    
    Args:
        device: Nautobot Device object
        
    Returns:
        SoftwareVersion object or None
    """
    # Check if device has software_version relationship
    if hasattr(device, 'software_version') and device.software_version:
        return device.software_version
    
    # Check SoftwareImageFile assignments
    if hasattr(device, 'software_image_files'):
        files = device.software_image_files.all()
        if files:
            # Get version from first assigned image file
            first_file = files.first()
            if hasattr(first_file, 'software_version'):
                return first_file.software_version
    
    return None


def find_template_for_device(
    device: Device,
    service: "PortService",
    as_of_date: date = None,
) -> Optional["ConfigTemplate"]:
    """
    Find the best matching ConfigTemplate for a device + service.
    
    Uses the new matching hierarchy:
    1. First try: Manufacturer + Platform + SoftwareVersion (most specific)
    2. Fallback: Manufacturer + Platform (no version)
    3. Legacy: SwitchProfile pattern matching
    
    Args:
        device: Nautobot Device object
        service: PortService object to find template for
        as_of_date: Optional date for historical lookup (defaults to today)
        
    Returns:
        ConfigTemplate object or None if no match found
    """
    from nautobot_network_provisioning.models import ConfigTemplate, SwitchProfile
    
    if as_of_date is None:
        as_of_date = date.today()
    
    # Get device attributes for matching
    manufacturer = device.device_type.manufacturer if device.device_type else None
    platform = device.platform
    software_version = get_device_software_version(device)
    
    # Try new matching hierarchy first
    if manufacturer and platform:
        template = _find_template_new_matching(
            service=service,
            manufacturer=manufacturer,
            platform=platform,
            software_version=software_version,
            as_of_date=as_of_date,
        )
        if template:
            return template
    
    # Fallback to legacy SwitchProfile matching
    return _find_template_legacy_matching(device, service)


def _find_template_new_matching(
    service: "PortService",
    manufacturer: "Manufacturer",
    platform: "Platform",
    software_version: "SoftwareVersion" = None,
    as_of_date: date = None,
) -> Optional["ConfigTemplate"]:
    """
    Find template using new Manufacturer/Platform/Version matching.
    
    Matching priority:
    1. Exact match: Manufacturer + Platform + SoftwareVersion (via M2M)
    2. Generic match: Manufacturer + Platform (no software versions)
    3. Manufacturer only: Manufacturer (no platform restriction)
    
    Within each level, selects the most recent active template by effective_date.
    
    Args:
        service: PortService object
        manufacturer: Manufacturer object
        platform: Platform object
        software_version: Optional SoftwareVersion object
        as_of_date: Date for template validity check
        
    Returns:
        ConfigTemplate object or None
    """
    from nautobot_network_provisioning.models import ConfigTemplate
    
    if as_of_date is None:
        as_of_date = date.today()
    
    # Base query: active templates for this service
    base_query = ConfigTemplate.objects.filter(
        service=service,
        is_active=True,
        effective_date__lte=as_of_date,
    )
    
    # Try 1: Exact match with software version via M2M field
    if software_version:
        # Filter by software_versions M2M relationship
        template = base_query.filter(
            manufacturer=manufacturer,
            platform=platform,
            software_versions=software_version,
        ).order_by('-effective_date', '-version').first()
        
        if template:
            return template
    
    # Try 2: Match without software version (generic platform template)
    # A template is "generic" if it has no software_versions assigned
    template = base_query.filter(
        manufacturer=manufacturer,
        platform=platform,
    ).exclude(
        software_versions__isnull=False  # Exclude templates with any versions
    ).order_by('-effective_date', '-version').first()
    
    # If no template without versions, try any template for manufacturer+platform
    if not template:
        template = base_query.filter(
            manufacturer=manufacturer,
            platform=platform,
        ).order_by('-effective_date', '-version').first()
    
    if template:
        return template
    
    # Try 3: Match with manufacturer only (any platform for this manufacturer)
    template = base_query.filter(
        manufacturer=manufacturer,
        platform__isnull=True,
    ).order_by('-effective_date', '-version').first()
    
    return template


def _find_template_legacy_matching(
    device: Device,
    service: "PortService",
) -> Optional["ConfigTemplate"]:
    """
    Legacy template matching using SwitchProfile patterns.
    
    Matches device type and OS version against SwitchProfile patterns.
    Returns the highest version template for the best matching profile.
    
    Args:
        device: Nautobot Device object
        service: PortService object to find template for
        
    Returns:
        ConfigTemplate object or None if no match found
    """
    from nautobot_network_provisioning.models import ConfigTemplate, SwitchProfile
    
    device_model = get_device_model(device)
    os_version = get_device_os_version(device)
    
    # Find matching switch profiles ordered by priority
    matching_profiles = []
    for profile in SwitchProfile.objects.all().order_by("priority"):
        # Check platform restriction if set
        if profile.platform and device.platform != profile.platform:
            continue
        
        # Check device type pattern
        if not _pattern_match(device_model, profile.device_type_pattern):
            continue
        
        # Check OS version pattern
        if not _pattern_match(os_version, profile.os_version_pattern):
            continue
        
        matching_profiles.append(profile)
    
    if not matching_profiles:
        return None
    
    # Get highest version template for best matching profile
    for profile in matching_profiles:
        template = ConfigTemplate.objects.filter(
            service=service,
            switch_profile=profile,
            is_active=True,
        ).order_by("-version").first()
        
        if template:
            return template
    
    return None


def find_all_matching_templates(
    device: Device,
    service: "PortService" = None,
) -> List["ConfigTemplate"]:
    """
    Find all templates that could match a device.
    
    Useful for debugging template matching issues.
    Returns templates ordered by match specificity.
    
    Args:
        device: Nautobot Device object
        service: Optional PortService to filter by
        
    Returns:
        List of matching ConfigTemplate objects
    """
    from nautobot_network_provisioning.models import ConfigTemplate
    
    manufacturer = device.device_type.manufacturer if device.device_type else None
    platform = device.platform
    software_version = get_device_software_version(device)
    
    matching = []
    
    # Build query for new matching
    query = Q(is_active=True)
    
    if service:
        query &= Q(service=service)
    
    if manufacturer:
        # Exact matches with software version via M2M (most specific first)
        if software_version:
            exact_match = ConfigTemplate.objects.filter(
                query,
                manufacturer=manufacturer,
                platform=platform,
                software_versions=software_version,
            ).order_by('-effective_date', '-version')
            matching.extend(list(exact_match))
        
        # Platform matches (templates without version restrictions)
        if platform:
            platform_match = ConfigTemplate.objects.filter(
                query,
                manufacturer=manufacturer,
                platform=platform,
            ).exclude(
                pk__in=[t.pk for t in matching]  # Exclude already added
            ).order_by('-effective_date', '-version')
            matching.extend(list(platform_match))
        
        # Manufacturer-only matches
        mfr_match = ConfigTemplate.objects.filter(
            query,
            manufacturer=manufacturer,
            platform__isnull=True,
        ).exclude(
            pk__in=[t.pk for t in matching]
        ).order_by('-effective_date', '-version')
        matching.extend(list(mfr_match))
    
    # Also include legacy profile matches
    legacy_profiles = find_all_matching_profiles(device)
    for profile in legacy_profiles:
        legacy_query = Q(switch_profile=profile, is_active=True)
        if service:
            legacy_query &= Q(service=service)
        
        legacy_templates = ConfigTemplate.objects.filter(legacy_query).order_by('-version')
        matching.extend(list(legacy_templates))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_matching = []
    for template in matching:
        if template.pk not in seen:
            seen.add(template.pk)
            unique_matching.append(template)
    
    return unique_matching


def find_all_matching_profiles(device: Device) -> list:
    """
    Find all SwitchProfiles that match a device.
    
    Useful for debugging template matching issues.
    
    Args:
        device: Nautobot Device object
        
    Returns:
        List of matching SwitchProfile objects
    """
    from nautobot_network_provisioning.models import SwitchProfile
    
    device_model = get_device_model(device)
    os_version = get_device_os_version(device)
    
    matching = []
    for profile in SwitchProfile.objects.all().order_by("priority"):
        if profile.platform and device.platform != profile.platform:
            continue
        
        if not _pattern_match(device_model, profile.device_type_pattern):
            continue
        
        if not _pattern_match(os_version, profile.os_version_pattern):
            continue
        
        matching.append(profile)
    
    return matching


def get_template_by_criteria(
    service: "PortService",
    manufacturer: "Manufacturer",
    platform: "Platform",
    software_version: "SoftwareVersion" = None,
    include_inactive: bool = False,
) -> Optional["ConfigTemplate"]:
    """
    Get a template by explicit matching criteria.
    
    Useful for direct template lookup without a device object.
    
    Args:
        service: PortService object
        manufacturer: Manufacturer object
        platform: Platform object
        software_version: Optional SoftwareVersion object
        include_inactive: Whether to include inactive templates
        
    Returns:
        ConfigTemplate object or None
    """
    from nautobot_network_provisioning.models import ConfigTemplate
    
    base_query = Q(
        service=service,
        manufacturer=manufacturer,
        platform=platform,
    )
    
    if not include_inactive:
        base_query &= Q(is_active=True)
    
    if software_version:
        # Match templates that include this software version in M2M
        template = ConfigTemplate.objects.filter(
            base_query,
            software_versions=software_version,
        ).order_by('-effective_date', '-version').first()
        
        if template:
            return template
    
    # Fallback: templates without version restrictions
    return ConfigTemplate.objects.filter(base_query).order_by(
        '-effective_date', '-version'
    ).first()
