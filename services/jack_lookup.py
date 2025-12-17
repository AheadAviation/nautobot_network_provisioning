"""
Jack lookup service for Building/Room/Jack to Device/Interface resolution.

Supports multiple lookup strategies:
1. JackMapping table (custom app table)
2. FrontPort with Location hierarchy (Nautobot native)
3. Interface custom fields (netdisco_building_name, netdisco_comm_room, netdisco_jack)
"""

from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from django.db.models import Q

from nautobot.dcim.models import Device, Interface, Location, FrontPort, RearPort, Cable


@dataclass
class JackLookupResult:
    """Result of a jack lookup operation."""
    device: Device
    interface: Interface
    building_name: str = ""
    comm_room: str = ""
    jack: str = ""
    lookup_source: str = ""  # 'jack_mapping', 'frontport', 'interface_cf'
    frontport: FrontPort = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device.name if self.device else "",
            "interface": self.interface.name if self.interface else "",
            "building_name": self.building_name,
            "comm_room": self.comm_room,
            "jack": self.jack,
            "lookup_source": self.lookup_source,
        }


def find_interface_by_jack(
    building_name: str,
    comm_room: str,
    jack: str,
) -> Tuple["JackMapping", Device, Interface]:
    """
    Find Device + Interface from Building/Room/Jack using JackMapping table.
    
    Args:
        building_name: Building name (partial match, case-insensitive)
        comm_room: Communications room identifier
        jack: Jack identifier
        
    Returns:
        Tuple of (JackMapping, Device, Interface)
        
    Raises:
        ValueError: If building not found or no jack mapping exists
    """
    from nautobot_network_provisioning.models import JackMapping
    
    # Find building (case-insensitive partial match)
    building = Location.objects.filter(
        name__icontains=building_name
    ).first()
    
    if not building:
        raise ValueError(f"Building not found: {building_name}")
    
    # Find the jack mapping
    mapping = JackMapping.objects.filter(
        building=building,
        comm_room__iexact=comm_room,
        jack__iexact=jack,
        is_active=True
    ).select_related("device", "interface").first()
    
    if not mapping:
        raise ValueError(
            f"No jack mapping found for {building_name}/{comm_room}/{jack}"
        )
    
    return mapping, mapping.device, mapping.interface


def find_interface_via_frontport(
    building_name: str,
    comm_room: str = "",
    jack: str = "",
) -> List[JackLookupResult]:
    """
    Find interfaces via FrontPort and Location hierarchy.
    
    This mimics nact.py's approach of using Nautobot's native data model:
    - FrontPort.device.location matches the building
    - FrontPort name or description contains comm_room/jack info
    
    Args:
        building_name: Building name (partial match)
        comm_room: Communications room (optional, for filtering)
        jack: Jack identifier (optional, for filtering)
        
    Returns:
        List of JackLookupResult objects
    """
    results = []
    
    # Find building locations
    buildings = Location.objects.filter(name__icontains=building_name)
    if not buildings.exists():
        return results
    
    # Get devices in these buildings
    devices = Device.objects.filter(location__in=buildings)
    
    # Find FrontPorts on these devices
    frontports = FrontPort.objects.filter(device__in=devices)
    
    # Apply additional filters if provided
    if comm_room:
        frontports = frontports.filter(
            Q(name__icontains=comm_room) | Q(description__icontains=comm_room)
        )
    
    if jack:
        frontports = frontports.filter(
            Q(name__icontains=jack) | Q(description__icontains=jack)
        )
    
    frontports = frontports.select_related("device", "device__location", "rear_port")
    
    for frontport in frontports:
        # Try to find associated interface
        interface = get_interface_from_frontport(frontport)
        if interface:
            results.append(JackLookupResult(
                device=frontport.device,
                interface=interface,
                building_name=frontport.device.location.name if frontport.device.location else "",
                comm_room=comm_room,
                jack=jack or frontport.name,
                lookup_source="frontport",
                frontport=frontport,
            ))
    
    return results


def get_interface_from_frontport(frontport: FrontPort) -> Optional[Interface]:
    """
    Get the Interface associated with a FrontPort.
    
    Tries multiple strategies:
    1. FrontPort -> RearPort -> Interface (via cable or direct connection)
    2. FrontPort name matching Interface name on same device
    3. FrontPort name pattern matching Interface name
    
    Args:
        frontport: FrontPort object to resolve
        
    Returns:
        Interface object if found, None otherwise
    """
    if not frontport:
        return None
    
    device = frontport.device
    if not device:
        return None
    
    # Strategy 1: Check if FrontPort has a rear_port that might connect to an Interface
    if hasattr(frontport, "rear_port") and frontport.rear_port:
        rear_port = frontport.rear_port
        
        # Try exact name match first
        interface = Interface.objects.filter(
            device=device,
            name=rear_port.name
        ).first()
        if interface:
            return interface
        
        # Try partial match with rear_port name
        interfaces = Interface.objects.filter(device=device)
        for intf in interfaces:
            if intf.name and rear_port.name:
                if (intf.name == rear_port.name or
                    intf.name.endswith(rear_port.name) or
                    rear_port.name in intf.name):
                    return intf
    
    # Strategy 2: Check if FrontPort name directly matches an Interface name
    if frontport.name:
        interface = Interface.objects.filter(
            device=device,
            name=frontport.name
        ).first()
        if interface:
            return interface
        
        # Strategy 3: Try pattern matching
        frontport_name_clean = frontport.name.replace(" ", "").upper()
        interfaces = Interface.objects.filter(device=device)
        for intf in interfaces:
            if intf.name:
                intf_name_clean = intf.name.replace(" ", "").upper()
                if (frontport_name_clean == intf_name_clean or
                    frontport_name_clean in intf_name_clean or
                    intf_name_clean in frontport_name_clean or
                    frontport.name in intf.name or
                    intf.name in frontport.name):
                    return intf
    
    # Strategy 4: If FrontPort has a cable, try to find Interface on the other end
    if hasattr(frontport, "cable") and frontport.cable:
        cable = frontport.cable
        if hasattr(cable, "termination_a") and cable.termination_a:
            if isinstance(cable.termination_a, Interface):
                return cable.termination_a
        if hasattr(cable, "termination_b") and cable.termination_b:
            if isinstance(cable.termination_b, Interface):
                return cable.termination_b
    
    return None


def find_interface_via_custom_fields(
    building_name: str,
    comm_room: str = "",
    jack: str = "",
) -> List[JackLookupResult]:
    """
    Find interfaces via NetDisco-style custom fields on Interface.
    
    Looks for interfaces with custom fields:
    - netdisco_building_name
    - netdisco_comm_room
    - netdisco_jack
    
    Args:
        building_name: Building name (partial match)
        comm_room: Communications room (optional)
        jack: Jack identifier (optional)
        
    Returns:
        List of JackLookupResult objects
    """
    results = []
    
    # Build custom field query
    cf_query = Q(_custom_field_data__netdisco_building_name__icontains=building_name)
    
    if comm_room:
        cf_query &= Q(_custom_field_data__netdisco_comm_room__iexact=comm_room)
    
    if jack:
        cf_query &= Q(_custom_field_data__netdisco_jack__iexact=jack)
    
    interfaces = Interface.objects.filter(cf_query).select_related("device", "device__location")
    
    for interface in interfaces:
        cf_data = interface.custom_field_data or {}
        results.append(JackLookupResult(
            device=interface.device,
            interface=interface,
            building_name=cf_data.get("netdisco_building_name", ""),
            comm_room=cf_data.get("netdisco_comm_room", ""),
            jack=cf_data.get("netdisco_jack", ""),
            lookup_source="interface_cf",
        ))
    
    return results


def find_interface_unified(
    building_name: str,
    comm_room: str = "",
    jack: str = "",
    strategies: List[str] = None,
) -> List[JackLookupResult]:
    """
    Unified interface lookup using multiple strategies.
    
    Tries each strategy in order until results are found:
    1. JackMapping table (if available)
    2. FrontPort/Location hierarchy
    3. Interface custom fields
    
    Args:
        building_name: Building name (partial match)
        comm_room: Communications room (optional)
        jack: Jack identifier (optional)
        strategies: List of strategies to try ('jack_mapping', 'frontport', 'interface_cf')
                    If None, tries all strategies
        
    Returns:
        List of JackLookupResult objects from the first successful strategy
    """
    if strategies is None:
        strategies = ["jack_mapping", "frontport", "interface_cf"]
    
    results = []
    
    for strategy in strategies:
        if strategy == "jack_mapping":
            try:
                from nautobot_network_provisioning.models import JackMapping
                mapping, device, interface = find_interface_by_jack(
                    building_name, comm_room, jack
                )
                results.append(JackLookupResult(
                    device=device,
                    interface=interface,
                    building_name=mapping.building.name if mapping.building else building_name,
                    comm_room=mapping.comm_room,
                    jack=mapping.jack,
                    lookup_source="jack_mapping",
                ))
            except (ValueError, ImportError):
                pass
        
        elif strategy == "frontport":
            results.extend(find_interface_via_frontport(building_name, comm_room, jack))
        
        elif strategy == "interface_cf":
            results.extend(find_interface_via_custom_fields(building_name, comm_room, jack))
        
        # Return if we found results
        if results:
            return results
    
    return results


def find_interface_by_jack_flexible(
    building_name: Optional[str] = None,
    comm_room: Optional[str] = None,
    jack: Optional[str] = None,
) -> list:
    """
    Flexible jack lookup with partial matching using JackMapping table.
    
    Returns a list of matching JackMappings for the given criteria.
    Any parameter can be None to skip that filter.
    
    Args:
        building_name: Building name (partial match, case-insensitive)
        comm_room: Communications room identifier (exact match, case-insensitive)
        jack: Jack identifier (partial match, case-insensitive)
        
    Returns:
        List of JackMapping objects matching the criteria
    """
    from nautobot_network_provisioning.models import JackMapping
    
    queryset = JackMapping.objects.filter(is_active=True)
    
    if building_name:
        queryset = queryset.filter(building__name__icontains=building_name)
    
    if comm_room:
        queryset = queryset.filter(comm_room__iexact=comm_room)
    
    if jack:
        queryset = queryset.filter(jack__icontains=jack)
    
    return list(
        queryset.select_related("building", "device", "interface")
        .order_by("building__name", "comm_room", "jack")
    )


def get_all_buildings_with_jacks() -> list:
    """
    Get a list of all buildings that have jack mappings.
    
    Returns:
        List of Location objects that have associated jack mappings
    """
    from nautobot_network_provisioning.models import JackMapping
    
    building_ids = JackMapping.objects.filter(
        is_active=True
    ).values_list("building_id", flat=True).distinct()
    
    return list(Location.objects.filter(id__in=building_ids).order_by("name"))


def get_all_buildings() -> list:
    """
    Get a list of all buildings (Locations) that could have jacks.
    
    Includes buildings from JackMapping table AND buildings with devices 
    that have FrontPorts.
    
    Returns:
        List of Location objects
    """
    from nautobot_network_provisioning.models import JackMapping
    
    # Get buildings from JackMapping
    jack_mapping_buildings = set(
        JackMapping.objects.filter(is_active=True)
        .values_list("building_id", flat=True)
    )
    
    # Get buildings with devices that have FrontPorts
    frontport_buildings = set(
        FrontPort.objects.all()
        .values_list("device__location_id", flat=True)
        .distinct()
    )
    
    all_building_ids = jack_mapping_buildings | frontport_buildings
    all_building_ids.discard(None)
    
    return list(
        Location.objects.filter(id__in=all_building_ids)
        .order_by("name")
    )


def get_comm_rooms_for_building(building: Location) -> list:
    """
    Get all communications rooms for a given building.
    
    Combines data from JackMapping table and FrontPort descriptions.
    
    Args:
        building: The building Location object
        
    Returns:
        List of unique comm_room values for the building
    """
    from nautobot_network_provisioning.models import JackMapping
    
    comm_rooms = set()
    
    # From JackMapping
    jack_comm_rooms = JackMapping.objects.filter(
        building=building,
        is_active=True
    ).values_list("comm_room", flat=True).distinct()
    comm_rooms.update(jack_comm_rooms)
    
    # From Interface custom fields
    interfaces = Interface.objects.filter(
        device__location=building
    ).exclude(
        _custom_field_data__netdisco_comm_room__isnull=True
    ).exclude(
        _custom_field_data__netdisco_comm_room=""
    )
    for intf in interfaces:
        cf_data = intf.custom_field_data or {}
        if cf_data.get("netdisco_comm_room"):
            comm_rooms.add(cf_data["netdisco_comm_room"])
    
    return sorted(list(comm_rooms))


def get_jacks_for_comm_room(building: Location, comm_room: str) -> list:
    """
    Get all jacks for a given building and communications room.
    
    Args:
        building: The building Location object
        comm_room: The communications room identifier
        
    Returns:
        List of JackMapping objects for the comm room
    """
    from nautobot_network_provisioning.models import JackMapping
    
    return list(
        JackMapping.objects.filter(
            building=building,
            comm_room__iexact=comm_room,
            is_active=True
        ).select_related("device", "interface").order_by("jack")
    )


def get_devices_for_building(building: Location) -> list:
    """
    Get all devices in a given building.
    
    Args:
        building: The building Location object
        
    Returns:
        List of Device objects in the building
    """
    return list(
        Device.objects.filter(location=building)
        .select_related("device_type", "role", "platform")
        .order_by("name")
    )


def get_frontports_for_device(device: Device) -> list:
    """
    Get all FrontPorts for a device.
    
    Args:
        device: The Device object
        
    Returns:
        List of FrontPort objects
    """
    return list(
        FrontPort.objects.filter(device=device)
        .select_related("rear_port")
        .order_by("name")
    )
