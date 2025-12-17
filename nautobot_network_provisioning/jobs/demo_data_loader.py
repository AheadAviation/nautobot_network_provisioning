"""
Demo Data Loader for NetAccess App.

This job loads example data to help users understand how to use the app.
It includes:
- Port Services (service types from original TWIX tool)
- Switch Profiles (device type + OS version patterns)
- Configuration Templates (Jinja2 templates for each service/profile combination)
- Sample JackMappings (if locations and devices exist)
- Control Settings for system configuration

Based on original TWIX service definitions converted to modern Nautobot app patterns.
All templates are stored in the database and editable via the Nautobot GUI.

Templates support both Jinja2 syntax ({{ variable }}) and legacy TWIX syntax (__VAR__).
"""

import datetime
import ipaddress
import random

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from nautobot.apps.jobs import Job, BooleanVar, ChoiceVar, register_jobs
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    InterfaceTemplate,
    Location,
    LocationType,
    Manufacturer,
    Platform,
)
from nautobot.extras.models import GraphQLQuery, Role, Status
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices

from nautobot_network_provisioning.jobs.device_type_importer import DEFAULT_DEVICE_TYPES, import_device_types

# ============================================================================
# JINJA2 CONFIGURATION TEMPLATES
# ============================================================================
# These templates support both Jinja2 ({{ variable }}) and legacy TWIX (__VAR__)
# syntax via the template_renderer service.
#
# Template Variables Available:
#   Device: device_name, device_ip, model, platform, site, role
#   Location: building_name, comm_room, jack
#   Service: service_name, vlan, voice_vlan
#   Audit: requested_by, DATE_APPLIED, timestamp
#   Interface: interface_name, interface (alias)
#   Legacy TWIX: __BUILDING__, __COMM_ROOM__, __JACK__, __SWITCH__, etc.

# -----------------------------------------------------------------------------
# CORE ACCESS PORT TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_ACCESS_DATA = """!
! ============================================================
! Port Configuration: {{ service_name }}
! Device: {{ device_name }} ({{ device_ip }})
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} {{ service_name | default("Data") }}
 switchport mode access
 switchport access vlan {{ vlan | default(290) }}
 switchport voice vlan {{ voice_vlan | default(293) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_ACCESS_VOIP = """!
! ============================================================
! VoIP Port Configuration
! Device: {{ device_name }} ({{ device_ip }})
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} VoIP
 switchport mode access
 switchport access vlan {{ data_vlan | default(290) }}
 switchport voice vlan {{ voice_vlan | default(293) }}
 authentication host-mode multi-auth
 authentication port-control auto
 mab
 dot1x pae authenticator
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_VOIP_CONVERGED = """!
! ============================================================
! Converged VoIP Port Configuration (802.1X with Voice)
! Device: {{ device_name }} ({{ device_ip }})
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} Converged-VoIP
 switchport mode access
 switchport access vlan {{ data_vlan | default(290) }}
 switchport voice vlan {{ voice_vlan | default(293) }}
 authentication host-mode multi-domain
 authentication port-control auto
 authentication periodic
 authentication timer reauthenticate 3600
 mab
 dot1x pae authenticator
 dot1x timeout tx-period 3
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# WIRELESS ACCESS POINT TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_WLAN_AP_STANDARD = """!
! ============================================================
! Wireless AP Port Configuration
! Device: {{ device_name }} ({{ device_ip }})
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} WLAN-AP
 switchport mode trunk
 switchport trunk native vlan {{ native_vlan | default(1) }}
 switchport trunk allowed vlan {{ allowed_vlans | default("1,10,20,30") }}
 switchport nonegotiate
 spanning-tree portfast trunk
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_WLAN_AP_2602 = """!
! ============================================================
! Cisco 2602 Series AP Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AP-2602
 switchport mode trunk
 switchport trunk native vlan {{ native_vlan | default(890) }}
 switchport trunk allowed vlan {{ allowed_vlans | default("890,891,892") }}
 switchport nonegotiate
 spanning-tree portfast trunk
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_WLAN_AP_3602 = """!
! ============================================================
! Cisco 3602 Series AP Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AP-3602
 switchport mode trunk
 switchport trunk native vlan {{ native_vlan | default(890) }}
 switchport trunk allowed vlan {{ allowed_vlans | default("890,891,892,893") }}
 switchport nonegotiate
 spanning-tree portfast trunk
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_WLAN_AP_3702 = """!
! ============================================================
! Cisco 3702 Series AP Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AP-3702
 switchport mode trunk
 switchport trunk native vlan {{ native_vlan | default(900) }}
 switchport trunk allowed vlan {{ allowed_vlans | default("900,901,902,903") }}
 switchport nonegotiate
 macro apply EtherChannel
 spanning-tree portfast trunk
 no shutdown
!
"""

TEMPLATE_WLAN_AP_MANAGEMENT = """!
! ============================================================
! WLAN Management Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} WLAN-MGMT
 switchport mode access
 switchport access vlan {{ management_vlan | default(890) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_WLAN_AP_MANAGEMENT_RES = """!
! ============================================================
! WLAN Residential Management Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} WLAN-MGMT-RES
 switchport mode access
 switchport access vlan {{ res_management_vlan | default(895) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# AV/MEDIA TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_AV_AUDIO_V287 = """!
! ============================================================
! AV Audio Port Configuration (VLAN 287)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AV-Audio
 switchport mode access
 switchport access vlan 287
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_AV_AUDIO_V288 = """!
! ============================================================
! AV Audio Port Configuration (VLAN 288)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AV-Audio
 switchport mode access
 switchport access vlan 288
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_AV_COLLABORATION = """!
! ============================================================
! AV Collaboration Port Configuration (VLAN 286)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AV-Collab
 switchport mode access
 switchport access vlan 286
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_AV_MANAGEMENT = """!
! ============================================================
! AV Management Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AV-MGMT
 switchport mode access
 switchport access vlan {{ av_management_vlan | default(285) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_AVOIP_TRANSPORT_V283 = """!
! ============================================================
! AVoIP Transport Port Configuration (VLAN 283)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AVoIP-Transport
 switchport mode trunk
 switchport trunk native vlan 283
 switchport trunk allowed vlan 283,284,285
 spanning-tree portfast trunk
 no shutdown
!
"""

TEMPLATE_AVOIP_TRANSPORT_V284 = """!
! ============================================================
! AVoIP Transport Port Configuration (VLAN 284)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} AVoIP-Transport
 switchport mode trunk
 switchport trunk native vlan 284
 switchport trunk allowed vlan 283,284,285
 spanning-tree portfast trunk
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# DEPARTMENT WORKSTATION TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_WORKSTATION_STANDARD = """!
! ============================================================
! Standard Workstation Port Configuration
! Device: {{ device_name }}
! Department: {{ department | default("General") }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} {{ department | default("WKS") }}
 switchport mode access
 switchport access vlan {{ vlan | default(290) }}
 switchport voice vlan {{ voice_vlan | default(293) }}
 authentication host-mode multi-auth
 authentication port-control auto
 mab
 dot1x pae authenticator
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_WORKSTATION_CONVERGED = """!
! ============================================================
! Converged Workstation Port Configuration (802.1X + Voice)
! Device: {{ device_name }}
! Department: {{ department | default("General") }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} {{ department | default("WKS-Conv") }}
 switchport mode access
 switchport access vlan {{ vlan | default(290) }}
 switchport voice vlan {{ voice_vlan | default(293) }}
 authentication host-mode multi-domain
 authentication port-control auto
 authentication periodic
 authentication timer reauthenticate 3600
 mab
 dot1x pae authenticator
 dot1x timeout tx-period 3
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_WORKSTATION_PROTECTED = """!
! ============================================================
! Protected Workstation Port Configuration (Port Security)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} Protected
 switchport mode access
 switchport access vlan {{ vlan | default(299) }}
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 switchport port-security aging time 60
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# LAB WORKSTATION TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_LAB_WORKSTATION = """!
! ============================================================
! Lab Workstation Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! VLAN: {{ vlan | default(304) }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} LAB
 switchport mode access
 switchport access vlan {{ vlan | default(304) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_LAB_EECS = """!
! ============================================================
! EECS Lab Workstation Port Configuration (VLAN 311)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} LAB-EECS
 switchport mode access
 switchport access vlan 311
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# RESIDENTIAL NETWORK TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_RESNET_UGRAD = """!
! ============================================================
! ResNet Undergraduate Port Configuration (VLAN 300)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} ResNet-Ugrad
 switchport mode access
 switchport access vlan 300
 authentication host-mode multi-auth
 authentication port-control auto
 mab
 dot1x pae authenticator
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_RESNET_EMPLOYEE = """!
! ============================================================
! ResNet Employee Port Configuration (VLAN 301)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} ResNet-Emp
 switchport mode access
 switchport access vlan 301
 authentication host-mode multi-auth
 authentication port-control auto
 mab
 dot1x pae authenticator
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_RESNET_VOIP_CONVERGED = """!
! ============================================================
! ResNet Converged VoIP Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} ResNet-VoIP
 switchport mode access
 switchport access vlan {{ data_vlan | default(300) }}
 switchport voice vlan {{ voice_vlan | default(302) }}
 authentication host-mode multi-domain
 authentication port-control auto
 mab
 dot1x pae authenticator
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_RESNET_DATA_AP702W = """!
! ============================================================
! ResNet Data Port with AP702W Support
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} ResNet-Data-AP702W
 switchport mode access
 switchport access vlan {{ data_vlan | default(289) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# SPECIAL PURPOSE TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_PRINTING = """!
! ============================================================
! Network Printer Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} Printer
 switchport mode access
 switchport access vlan {{ printing_vlan | default(295) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_YUCARD = """!
! ============================================================
! YUcard System Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} YUcard
 switchport mode access
 switchport access vlan {{ yucard_vlan | default(296) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_PARKING = """!
! ============================================================
! Parking System Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} Parking
 switchport mode access
 switchport access vlan {{ parking_vlan | default(297) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_BAS = """!
! ============================================================
! Building Automation System Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} BAS
 switchport mode access
 switchport access vlan {{ bas_vlan | default(298) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_PAS = """!
! ============================================================
! Physical Access System (Door Control) Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} PAS
 switchport mode access
 switchport access vlan {{ pas_vlan | default(294) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_EMDSS = """!
! ============================================================
! EMDSS System Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} EMDSS
 switchport mode access
 switchport access vlan {{ emdss_vlan | default(291) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_CDAC = """!
! ============================================================
! CDAC System Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} CDAC
 switchport mode access
 switchport access vlan {{ cdac_vlan | default(292) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

TEMPLATE_DATAROOM_MANAGEMENT = """!
! ============================================================
! Data Room Management Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} DataRoom-MGMT
 switchport mode access
 switchport access vlan {{ management_vlan | default(10) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# UNUSED PORT TEMPLATE
# -----------------------------------------------------------------------------

TEMPLATE_UNUSED_PORT = """!
! ============================================================
! Unused Port - DISABLED
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} UNUSED
 switchport mode access
 switchport access vlan {{ unused_vlan | default(999) }}
 shutdown
!
"""

# -----------------------------------------------------------------------------
# UTILITY TEMPLATES - VLAN CHANGES, PORT ENABLE/DISABLE
# -----------------------------------------------------------------------------

TEMPLATE_CHANGE_VLAN = """!
! ============================================================
! Change VLAN Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! New VLAN: {{ vlan }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 switchport access vlan {{ vlan }}
!
"""

TEMPLATE_CHANGE_VOICE_VLAN = """!
! ============================================================
! Change Voice VLAN Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! New Voice VLAN: {{ voice_vlan }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 switchport voice vlan {{ voice_vlan }}
!
"""

TEMPLATE_ENABLE_PORT = """!
! ============================================================
! Enable Port (No Shutdown)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 no shutdown
!
"""

TEMPLATE_DISABLE_PORT = """!
! ============================================================
! Disable Port (Shutdown)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 shutdown
!
"""

TEMPLATE_CHANGE_DESCRIPTION = """!
! ============================================================
! Change Port Description
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description {{ description | default(building_name ~ "-" ~ comm_room ~ "-" ~ jack) }}
!
"""

TEMPLATE_CLEAR_CONFIG = """!
! ============================================================
! Clear Interface Configuration (Default)
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
default interface {{ interface_name }}
!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} CLEARED
 shutdown
!
"""

# -----------------------------------------------------------------------------
# TRUNK PORT TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_TRUNK_SWITCH = """!
! ============================================================
! Switch-to-Switch Trunk Port Configuration
! Device: {{ device_name }}
! Neighbor: {{ neighbor_device | default("UPLINK") }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
 description TRUNK-TO-{{ neighbor_device | default("UPLINK") }}
 switchport mode trunk
 switchport trunk native vlan {{ native_vlan | default(1) }}
 switchport trunk allowed vlan {{ allowed_vlans | default("all") }}
 channel-group {{ channel_group | default(1) }} mode active
 no shutdown
!
"""

# -----------------------------------------------------------------------------
# NEXUS (NX-OS) SPECIFIC TEMPLATES
# -----------------------------------------------------------------------------

TEMPLATE_NXOS_ACCESS_DATA = """!
! ============================================================
! NX-OS Data Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
  description {{ building_name }}-{{ comm_room }}-{{ jack }} {{ service_name | default("Data") }}
  switchport mode access
  switchport access vlan {{ vlan | default(290) }}
  spanning-tree port type edge
  spanning-tree bpduguard enable
  no shutdown
!
"""

TEMPLATE_NXOS_ACCESS_VOIP = """!
! ============================================================
! NX-OS VoIP Port Configuration
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
  description {{ building_name }}-{{ comm_room }}-{{ jack }} VoIP
  switchport mode access
  switchport access vlan {{ data_vlan | default(290) }}
  switchport voice vlan {{ voice_vlan | default(293) }}
  spanning-tree port type edge
  spanning-tree bpduguard enable
  no shutdown
!
"""

TEMPLATE_NXOS_TRUNK = """!
! ============================================================
! NX-OS Trunk Port Configuration
! Device: {{ device_name }}
! Neighbor: {{ neighbor_device | default("UPLINK") }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
  description TRUNK-TO-{{ neighbor_device | default("UPLINK") }}
  switchport mode trunk
  switchport trunk native vlan {{ native_vlan | default(1) }}
  switchport trunk allowed vlan {{ allowed_vlans | default("all") }}
  spanning-tree port type normal
  no shutdown
!
"""

TEMPLATE_NXOS_UNUSED = """!
! ============================================================
! NX-OS Unused Port - DISABLED
! Device: {{ device_name }}
! Location: {{ building_name }} / {{ comm_room }} / {{ jack }}
! Applied: {{ DATE_APPLIED }} by {{ requested_by }}
! ============================================================
!
interface {{ interface_name }}
  description {{ building_name }}-{{ comm_room }}-{{ jack }} UNUSED
  switchport mode access
  switchport access vlan {{ unused_vlan | default(999) }}
  shutdown
!
"""


# ============================================================================
# TEMPLATE REGISTRY - Maps template keys to template content
# ============================================================================

DEMO_TEMPLATES = {
    # Core Access
    "access_data": TEMPLATE_ACCESS_DATA,
    "access_voip": TEMPLATE_ACCESS_VOIP,
    "voip_converged": TEMPLATE_VOIP_CONVERGED,
    
    # WLAN APs
    "wlan_ap_standard": TEMPLATE_WLAN_AP_STANDARD,
    "wlan_ap_2602": TEMPLATE_WLAN_AP_2602,
    "wlan_ap_3602": TEMPLATE_WLAN_AP_3602,
    "wlan_ap_3702": TEMPLATE_WLAN_AP_3702,
    "wlan_ap_management": TEMPLATE_WLAN_AP_MANAGEMENT,
    "wlan_ap_management_res": TEMPLATE_WLAN_AP_MANAGEMENT_RES,
    
    # AV/Media
    "av_audio_v287": TEMPLATE_AV_AUDIO_V287,
    "av_audio_v288": TEMPLATE_AV_AUDIO_V288,
    "av_collaboration": TEMPLATE_AV_COLLABORATION,
    "av_management": TEMPLATE_AV_MANAGEMENT,
    "avoip_transport_v283": TEMPLATE_AVOIP_TRANSPORT_V283,
    "avoip_transport_v284": TEMPLATE_AVOIP_TRANSPORT_V284,
    
    # Workstations
    "workstation_standard": TEMPLATE_WORKSTATION_STANDARD,
    "workstation_converged": TEMPLATE_WORKSTATION_CONVERGED,
    "workstation_protected": TEMPLATE_WORKSTATION_PROTECTED,
    
    # Labs
    "lab_workstation": TEMPLATE_LAB_WORKSTATION,
    "lab_eecs": TEMPLATE_LAB_EECS,
    
    # Residential
    "resnet_ugrad": TEMPLATE_RESNET_UGRAD,
    "resnet_employee": TEMPLATE_RESNET_EMPLOYEE,
    "resnet_voip_converged": TEMPLATE_RESNET_VOIP_CONVERGED,
    "resnet_data_ap702w": TEMPLATE_RESNET_DATA_AP702W,
    
    # Special Purpose
    "printing": TEMPLATE_PRINTING,
    "yucard": TEMPLATE_YUCARD,
    "parking": TEMPLATE_PARKING,
    "bas": TEMPLATE_BAS,
    "pas": TEMPLATE_PAS,
    "emdss": TEMPLATE_EMDSS,
    "cdac": TEMPLATE_CDAC,
    "dataroom_management": TEMPLATE_DATAROOM_MANAGEMENT,
    
    # Unused
    "unused_port": TEMPLATE_UNUSED_PORT,
    
    # Utility
    "change_vlan": TEMPLATE_CHANGE_VLAN,
    "change_voice_vlan": TEMPLATE_CHANGE_VOICE_VLAN,
    "enable_port": TEMPLATE_ENABLE_PORT,
    "disable_port": TEMPLATE_DISABLE_PORT,
    "change_description": TEMPLATE_CHANGE_DESCRIPTION,
    "clear_config": TEMPLATE_CLEAR_CONFIG,
    
    # Trunk
    "trunk_switch": TEMPLATE_TRUNK_SWITCH,
    
    # NX-OS Specific
    "nxos_access_data": TEMPLATE_NXOS_ACCESS_DATA,
    "nxos_access_voip": TEMPLATE_NXOS_ACCESS_VOIP,
    "nxos_trunk": TEMPLATE_NXOS_TRUNK,
    "nxos_unused": TEMPLATE_NXOS_UNUSED,
}


# ============================================================================
# PORT SERVICE DEFINITIONS - Based on TWIX services.sql
# ============================================================================

DEMO_PORT_SERVICES = [
    # Core Access Ports
    {"name": "Access-Data", "description": "Standard data port with optional VoIP VLAN", "is_active": True},
    {"name": "Access-VoIP", "description": "Voice over IP port with 802.1X/MAB", "is_active": True},
    {"name": "VoIP-Converged", "description": "Converged voice/data port with multi-domain 802.1X", "is_active": True},
    
    # Wireless Access Points
    {"name": "Access-WLAN-AP-2602", "description": "Cisco 2602 series access point port", "is_active": True},
    {"name": "Access-WLAN-AP-3602", "description": "Cisco 3602 series access point port", "is_active": True},
    {"name": "Access-WLAN-AP-3702", "description": "Cisco 3702 series access point port", "is_active": True},
    {"name": "Access-WLAN-AP-Management", "description": "WLAN controller/management port", "is_active": True},
    {"name": "Access-WLAN-AP-Management-RES", "description": "Residential WLAN management port", "is_active": True},
    
    # AV/Media
    {"name": "Access-AV-Audio-V287", "description": "AV audio system port (VLAN 287)", "is_active": True},
    {"name": "Access-AV-Audio-V288", "description": "AV audio system port (VLAN 288)", "is_active": True},
    {"name": "Access-AV-Collaboration-V286", "description": "AV collaboration room port (VLAN 286)", "is_active": True},
    {"name": "Access-AV-Management", "description": "AV system management port", "is_active": True},
    {"name": "Access-AVoIP-Transport-V283", "description": "AV over IP transport (VLAN 283)", "is_active": True},
    {"name": "Access-AVoIP-Transport-V284", "description": "AV over IP transport (VLAN 284)", "is_active": True},
    
    # Department Workstations
    {"name": "Access-CS-Workstation-V485", "description": "Computer Science workstation (VLAN 485)", "is_active": True},
    {"name": "Access-CS-Workstation-Converged-V485", "description": "CS workstation with converged voice (VLAN 485)", "is_active": True},
    {"name": "Access-CTS-Workstation-V843", "description": "CTS workstation (VLAN 843)", "is_active": True},
    {"name": "Access-CTS-Workstation-Converged-V843", "description": "CTS workstation with converged voice (VLAN 843)", "is_active": True},
    {"name": "Access-DBA-Workstation-V15", "description": "DBA workstation (VLAN 15)", "is_active": True},
    {"name": "Access-DBA-Workstation-Converged-V15", "description": "DBA workstation with converged voice (VLAN 15)", "is_active": True},
    {"name": "Access-NETSERVICES-Workstation-V16", "description": "Net Services workstation (VLAN 16)", "is_active": True},
    {"name": "Access-NETSERVICES-Workstation-Converged-V16", "description": "Net Services with converged voice (VLAN 16)", "is_active": True},
    {"name": "Access-SMS-Workstation-V59", "description": "SMS workstation (VLAN 59)", "is_active": True},
    {"name": "Access-SMS-Workstation-Converged-V59", "description": "SMS workstation with converged voice (VLAN 59)", "is_active": True},
    {"name": "Access-WTS-Workstation-V841", "description": "WTS workstation (VLAN 841)", "is_active": True},
    {"name": "Access-WTS-Workstation-Converged-V841", "description": "WTS workstation with converged voice (VLAN 841)", "is_active": True},
    {"name": "Access-Protected-Workstation-V299", "description": "Protected workstation with port security (VLAN 299)", "is_active": True},
    
    # Lab Workstations
    {"name": "Access-LAB-Workstation-V304", "description": "Lab workstation (VLAN 304)", "is_active": True},
    {"name": "Access-LAB-Workstation-V305", "description": "Lab workstation (VLAN 305)", "is_active": True},
    {"name": "Access-LAB-Workstation-V306", "description": "Lab workstation (VLAN 306)", "is_active": True},
    {"name": "Access-LAB-EECS-Workstation-V311", "description": "EECS Lab workstation (VLAN 311)", "is_active": True},
    
    # Residential Network
    {"name": "Access-ResNet-Ugrad-V300", "description": "Residence network undergraduate (VLAN 300)", "is_active": True},
    {"name": "Access-ResNet-Employee-V301", "description": "Residence network employee (VLAN 301)", "is_active": True},
    {"name": "VoIP-RES-Converged", "description": "Residential converged VoIP port", "is_active": True},
    {"name": "Access-Data-RES-AP702W", "description": "Residential data port with AP702W support", "is_active": True},
    {"name": "Access-Data-VoIP-RES-AP702W", "description": "Residential data+VoIP with AP702W", "is_active": True},
    
    # Special Purpose Systems
    {"name": "Access-Printing-Management", "description": "Network printer port", "is_active": True},
    {"name": "Access-YUcard", "description": "YUcard system port", "is_active": True},
    {"name": "Access-Parking", "description": "Parking system port", "is_active": True},
    {"name": "Access-BAS", "description": "Building automation system port", "is_active": True},
    {"name": "Access-PAS", "description": "Physical access system (door control)", "is_active": True},
    {"name": "Access-EMDSS", "description": "EMDSS system port", "is_active": True},
    {"name": "Access-CDAC", "description": "CDAC system port", "is_active": True},
    {"name": "Access-DataRoom-Management", "description": "Data room management port", "is_active": True},
    {"name": "Access-VSoIP", "description": "Video surveillance over IP port", "is_active": True},
    
    # Utility Operations
    {"name": "Unused-Port", "description": "Disabled/unused port configuration", "is_active": True},
    {"name": "Change-VLAN", "description": "Change data VLAN on existing port", "is_active": True},
    {"name": "Change-Voice-VLAN", "description": "Change voice VLAN on existing port", "is_active": True},
    {"name": "Enable-Port", "description": "Enable a shutdown port", "is_active": True},
    {"name": "Disable-Port", "description": "Disable/shutdown a port", "is_active": True},
    {"name": "Change-Description", "description": "Change port description only", "is_active": True},
    {"name": "Clear-Config", "description": "Clear interface to default state", "is_active": True},
    
    # Trunk Operations
    {"name": "Trunk-Switch", "description": "Switch-to-switch trunk port", "is_active": True},
]


# ============================================================================
# SWITCH PROFILE DEFINITIONS - Based on TWIX switch.sql
# ============================================================================

DEMO_SWITCH_PROFILES = [
    # Cisco Catalyst 2960 Series
    {"name": "Catalyst 2960C 15.2", "device_type_pattern": "WS-C2960C%", "os_version_pattern": "15.2(2)E%", "priority": 30},
    {"name": "Catalyst 2960CX 15.2", "device_type_pattern": "WS-C2960CX%", "os_version_pattern": "15.2(3)%", "priority": 30},
    {"name": "Catalyst 2960S 15.0", "device_type_pattern": "WS-C2960S%", "os_version_pattern": "15.0(2)SE%", "priority": 35},
    {"name": "Catalyst 2960X 15.2", "device_type_pattern": "WS-C2960X%", "os_version_pattern": "15.2(2)E%", "priority": 30},
    
    # Cisco Catalyst 3560 Series
    {"name": "Catalyst 3560 12.2 SE", "device_type_pattern": "WS-C3560%", "os_version_pattern": "12.%-SE%", "priority": 40},
    {"name": "Catalyst 3560C 12.2", "device_type_pattern": "WS-C3560C%", "os_version_pattern": "12.2(55)-SE%", "priority": 40},
    {"name": "Catalyst 3560CG 15.2", "device_type_pattern": "WS-C3560CG%", "os_version_pattern": "15.2(2)%", "priority": 35},
    {"name": "Catalyst 3560X 15.2(2)E", "device_type_pattern": "WS-C3560X%", "os_version_pattern": "15.2(2)E%", "priority": 25},
    {"name": "Catalyst 3560X 15.2(3)", "device_type_pattern": "WS-C3560X%", "os_version_pattern": "15.2(3)%", "priority": 25},
    
    # Cisco Catalyst 3750 Series
    {"name": "Catalyst 3750X 15.2", "device_type_pattern": "WS-C3750X%", "os_version_pattern": "15.2(2)E%", "priority": 25},
    
    # Cisco Catalyst 3850 Series (IOS-XE)
    {"name": "Catalyst 3850 3.x SE", "device_type_pattern": "WS-C3850%", "os_version_pattern": "3.%(%)E%", "priority": 15},
    {"name": "Catalyst 3850 16.x", "device_type_pattern": "WS-C3850%", "os_version_pattern": "16.%", "priority": 10},
    
    # Cisco Catalyst 9000 Series (IOS-XE 17.x)
    {"name": "Catalyst 9200", "device_type_pattern": "C9200%", "os_version_pattern": "17.%", "priority": 5},
    {"name": "Catalyst 9300", "device_type_pattern": "C9300%", "os_version_pattern": "17.%", "priority": 5},
    {"name": "Catalyst 9400", "device_type_pattern": "C9400%", "os_version_pattern": "17.%", "priority": 5},
    {"name": "Catalyst 9500", "device_type_pattern": "C9500%", "os_version_pattern": "17.%", "priority": 5},
    {"name": "Catalyst 9600", "device_type_pattern": "C9600%", "os_version_pattern": "17.%", "priority": 5},
    
    # Cisco Nexus Series (NX-OS)
    {"name": "Nexus 9000 9.3", "device_type_pattern": "N9K%", "os_version_pattern": "9.3%", "priority": 10},
    {"name": "Nexus 9000 10.x", "device_type_pattern": "N9K%", "os_version_pattern": "10.%", "priority": 5},
    {"name": "Nexus 7000", "device_type_pattern": "N7K%", "os_version_pattern": "%", "priority": 15},
    {"name": "Nexus 5000", "device_type_pattern": "N5K%", "os_version_pattern": "%", "priority": 20},
    {"name": "Nexus 3000", "device_type_pattern": "N3K%", "os_version_pattern": "%", "priority": 15},
    
    # Generic Fallbacks (highest priority number = lowest priority match)
    {"name": "Generic Cisco IOS 12.x", "device_type_pattern": "%", "os_version_pattern": "12.%", "priority": 200},
    {"name": "Generic Cisco IOS 15.x", "device_type_pattern": "%", "os_version_pattern": "15.%", "priority": 150},
    {"name": "Generic Cisco IOS-XE 16.x", "device_type_pattern": "%", "os_version_pattern": "16.%", "priority": 100},
    {"name": "Generic Cisco IOS-XE 17.x", "device_type_pattern": "%", "os_version_pattern": "17.%", "priority": 100},
    {"name": "Generic NX-OS", "device_type_pattern": "N%K%", "os_version_pattern": "%", "priority": 200},
]


# ============================================================================
# TEMPLATE MAPPINGS (Service -> Profile -> Template Key)
# Format: (service_name, profile_name, template_key, instance, version)
# ============================================================================

TEMPLATE_MAPPINGS = [
    # Core Access - IOS
    ("Access-Data", "Generic Cisco IOS 15.x", "access_data", 1, 1),
    ("Access-Data", "Generic Cisco IOS-XE 16.x", "access_data", 1, 1),
    ("Access-Data", "Generic Cisco IOS-XE 17.x", "access_data", 1, 1),
    ("Access-Data", "Catalyst 9300", "access_data", 1, 1),
    ("Access-Data", "Catalyst 3850 16.x", "access_data", 1, 1),
    ("Access-Data", "Generic NX-OS", "nxos_access_data", 2, 1),
    
    ("Access-VoIP", "Generic Cisco IOS 15.x", "access_voip", 1, 1),
    ("Access-VoIP", "Generic Cisco IOS-XE 16.x", "access_voip", 1, 1),
    ("Access-VoIP", "Generic Cisco IOS-XE 17.x", "access_voip", 1, 1),
    ("Access-VoIP", "Catalyst 9300", "access_voip", 1, 1),
    ("Access-VoIP", "Generic NX-OS", "nxos_access_voip", 2, 1),
    
    ("VoIP-Converged", "Generic Cisco IOS 15.x", "voip_converged", 1, 1),
    ("VoIP-Converged", "Generic Cisco IOS-XE 16.x", "voip_converged", 1, 1),
    ("VoIP-Converged", "Generic Cisco IOS-XE 17.x", "voip_converged", 1, 1),
    ("VoIP-Converged", "Catalyst 9300", "voip_converged", 1, 1),
    
    # WLAN APs
    ("Access-WLAN-AP-2602", "Generic Cisco IOS 15.x", "wlan_ap_2602", 1, 1),
    ("Access-WLAN-AP-2602", "Generic Cisco IOS-XE 17.x", "wlan_ap_2602", 1, 1),
    ("Access-WLAN-AP-3602", "Generic Cisco IOS 15.x", "wlan_ap_3602", 1, 1),
    ("Access-WLAN-AP-3602", "Generic Cisco IOS-XE 17.x", "wlan_ap_3602", 1, 1),
    ("Access-WLAN-AP-3702", "Generic Cisco IOS 15.x", "wlan_ap_3702", 1, 1),
    ("Access-WLAN-AP-3702", "Generic Cisco IOS-XE 17.x", "wlan_ap_3702", 1, 1),
    ("Access-WLAN-AP-3702", "Catalyst 9300", "wlan_ap_3702", 1, 1),
    ("Access-WLAN-AP-Management", "Generic Cisco IOS 15.x", "wlan_ap_management", 1, 1),
    ("Access-WLAN-AP-Management", "Generic Cisco IOS-XE 17.x", "wlan_ap_management", 1, 1),
    ("Access-WLAN-AP-Management-RES", "Generic Cisco IOS 15.x", "wlan_ap_management_res", 1, 1),
    
    # AV/Media
    ("Access-AV-Audio-V287", "Generic Cisco IOS 15.x", "av_audio_v287", 1, 1),
    ("Access-AV-Audio-V287", "Generic Cisco IOS-XE 17.x", "av_audio_v287", 1, 1),
    ("Access-AV-Audio-V288", "Generic Cisco IOS 15.x", "av_audio_v288", 1, 1),
    ("Access-AV-Audio-V288", "Generic Cisco IOS-XE 17.x", "av_audio_v288", 1, 1),
    ("Access-AV-Collaboration-V286", "Generic Cisco IOS 15.x", "av_collaboration", 1, 1),
    ("Access-AV-Collaboration-V286", "Generic Cisco IOS-XE 17.x", "av_collaboration", 1, 1),
    ("Access-AV-Management", "Generic Cisco IOS 15.x", "av_management", 1, 1),
    ("Access-AVoIP-Transport-V283", "Generic Cisco IOS 15.x", "avoip_transport_v283", 1, 1),
    ("Access-AVoIP-Transport-V283", "Generic Cisco IOS-XE 17.x", "avoip_transport_v283", 1, 1),
    ("Access-AVoIP-Transport-V284", "Generic Cisco IOS 15.x", "avoip_transport_v284", 1, 1),
    
    # Labs
    ("Access-LAB-Workstation-V304", "Generic Cisco IOS 15.x", "lab_workstation", 1, 1),
    ("Access-LAB-Workstation-V304", "Generic Cisco IOS-XE 17.x", "lab_workstation", 1, 1),
    ("Access-LAB-Workstation-V305", "Generic Cisco IOS 15.x", "lab_workstation", 1, 1),
    ("Access-LAB-Workstation-V306", "Generic Cisco IOS 15.x", "lab_workstation", 1, 1),
    ("Access-LAB-EECS-Workstation-V311", "Generic Cisco IOS 15.x", "lab_eecs", 1, 1),
    
    # Residential
    ("Access-ResNet-Ugrad-V300", "Generic Cisco IOS 15.x", "resnet_ugrad", 1, 1),
    ("Access-ResNet-Ugrad-V300", "Generic Cisco IOS-XE 17.x", "resnet_ugrad", 1, 1),
    ("Access-ResNet-Employee-V301", "Generic Cisco IOS 15.x", "resnet_employee", 1, 1),
    ("Access-ResNet-Employee-V301", "Generic Cisco IOS-XE 17.x", "resnet_employee", 1, 1),
    ("VoIP-RES-Converged", "Generic Cisco IOS 15.x", "resnet_voip_converged", 1, 1),
    ("Access-Data-RES-AP702W", "Generic Cisco IOS 15.x", "resnet_data_ap702w", 1, 1),
    
    # Special Purpose
    ("Access-Printing-Management", "Generic Cisco IOS 15.x", "printing", 1, 1),
    ("Access-Printing-Management", "Generic Cisco IOS-XE 17.x", "printing", 1, 1),
    ("Access-YUcard", "Generic Cisco IOS 15.x", "yucard", 1, 1),
    ("Access-YUcard", "Generic Cisco IOS-XE 17.x", "yucard", 1, 1),
    ("Access-Parking", "Generic Cisco IOS 15.x", "parking", 1, 1),
    ("Access-Parking", "Generic Cisco IOS-XE 17.x", "parking", 1, 1),
    ("Access-BAS", "Generic Cisco IOS 15.x", "bas", 1, 1),
    ("Access-BAS", "Generic Cisco IOS-XE 17.x", "bas", 1, 1),
    ("Access-PAS", "Generic Cisco IOS 15.x", "pas", 1, 1),
    ("Access-EMDSS", "Generic Cisco IOS 15.x", "emdss", 1, 1),
    ("Access-CDAC", "Generic Cisco IOS 15.x", "cdac", 1, 1),
    ("Access-DataRoom-Management", "Generic Cisco IOS 15.x", "dataroom_management", 1, 1),
    
    # Protected Workstations
    ("Access-Protected-Workstation-V299", "Generic Cisco IOS 15.x", "workstation_protected", 1, 1),
    ("Access-Protected-Workstation-V299", "Generic Cisco IOS-XE 17.x", "workstation_protected", 1, 1),
    
    # Unused
    ("Unused-Port", "Generic Cisco IOS 15.x", "unused_port", 1, 1),
    ("Unused-Port", "Generic Cisco IOS-XE 16.x", "unused_port", 1, 1),
    ("Unused-Port", "Generic Cisco IOS-XE 17.x", "unused_port", 1, 1),
    ("Unused-Port", "Catalyst 9300", "unused_port", 1, 1),
    ("Unused-Port", "Catalyst 3850 16.x", "unused_port", 1, 1),
    ("Unused-Port", "Generic NX-OS", "nxos_unused", 2, 1),
    
    # Utility Templates - Apply to all platforms
    ("Change-VLAN", "Generic Cisco IOS 15.x", "change_vlan", 1, 1),
    ("Change-VLAN", "Generic Cisco IOS-XE 17.x", "change_vlan", 1, 1),
    ("Change-Voice-VLAN", "Generic Cisco IOS 15.x", "change_voice_vlan", 1, 1),
    ("Change-Voice-VLAN", "Generic Cisco IOS-XE 17.x", "change_voice_vlan", 1, 1),
    ("Enable-Port", "Generic Cisco IOS 15.x", "enable_port", 1, 1),
    ("Enable-Port", "Generic Cisco IOS-XE 17.x", "enable_port", 1, 1),
    ("Disable-Port", "Generic Cisco IOS 15.x", "disable_port", 1, 1),
    ("Disable-Port", "Generic Cisco IOS-XE 17.x", "disable_port", 1, 1),
    ("Change-Description", "Generic Cisco IOS 15.x", "change_description", 1, 1),
    ("Change-Description", "Generic Cisco IOS-XE 17.x", "change_description", 1, 1),
    ("Clear-Config", "Generic Cisco IOS 15.x", "clear_config", 1, 1),
    ("Clear-Config", "Generic Cisco IOS-XE 17.x", "clear_config", 1, 1),
    
    # Trunk
    ("Trunk-Switch", "Generic Cisco IOS 15.x", "trunk_switch", 1, 1),
    ("Trunk-Switch", "Generic Cisco IOS-XE 17.x", "trunk_switch", 1, 1),
    ("Trunk-Switch", "Generic NX-OS", "nxos_trunk", 2, 1),
]


# ============================================================================
# CONTROL SETTINGS
# ============================================================================

DEMO_CONTROL_SETTINGS = [
    {"name": "queue_processing_enabled", "value": "true", "description": "Enable/disable work queue processing"},
    {"name": "write_mem_enabled", "value": "true", "description": "Enable/disable write memory after config push"},
    {"name": "config_backup_enabled", "value": "true", "description": "Enable/disable config backup before changes"},
    {"name": "dry_run_default", "value": "true", "description": "Default dry-run mode for new work queue entries"},
    {"name": "notification_enabled", "value": "false", "description": "Enable/disable email notifications"},
]


# ============================================================================
# JOB DEFINITION
# ============================================================================

class LoadDemoData(Job):
    """
    Load Demo Data for NetAccess App.
    
    This job populates the database with example Port Services, Switch Profiles,
    and Configuration Templates based on the original TWIX tool. All templates
    are stored in the database and editable via the Nautobot GUI.
    
    Templates support both Jinja2 syntax ({{ variable }}) and legacy TWIX syntax
    (__VAR__) for backwards compatibility.
    
    This is intended to be run once on a fresh installation to provide example
    data that helps users understand how the app works.
    """

    class Meta:
        name = "Load Demo Data"
        description = (
            "Load example Port Services, Switch Profiles, and Config Templates "
            "based on the original TWIX tool. All templates are GUI-editable."
        )
        commit_default = False
        has_sensitive_variables = False

    overwrite_existing = BooleanVar(
        description="Overwrite existing data if it exists (WARNING: This will replace templates!)",
        default=False,
    )
    
    data_set = ChoiceVar(
        description="Which data set to load",
        choices=[
            ("full", "Full Demo Data (All services, profiles, and templates)"),
            ("minimal", "Minimal (Core services + common templates only)"),
            ("utility_only", "Utility Templates Only (VLAN change, enable/disable, etc.)"),
        ],
        default="full",
    )
    
    load_services = BooleanVar(
        description="Load Port Service definitions",
        default=True,
    )
    
    load_profiles = BooleanVar(
        description="Load Switch Profile definitions",
        default=True,
    )
    
    load_templates = BooleanVar(
        description="Load Configuration Templates",
        default=True,
    )
    
    load_controls = BooleanVar(
        description="Load default Control Settings",
        default=True,
    )
    
    load_sample_jack_mappings = BooleanVar(
        description="Create sample Jack Mappings (requires existing Locations and Devices)",
        default=False,
    )

    load_device_types = BooleanVar(
        description="Import real DeviceTypes from nautobot/devicetype-library (GitHub)",
        default=True,
    )

    load_graphql_queries = BooleanVar(
        description="Create saved GraphQL queries for Template IDE (Extras > GraphQL Queries)",
        default=True,
    )

    load_operational_data = BooleanVar(
        description="Create operational demo data (MAC tables, ARP entries, history)",
        default=True,
    )

    load_work_queue_entries = BooleanVar(
        description="Create sample Work Queue entries (pending/completed/failed)",
        default=True,
    )

    def run(self, **kwargs):
        """Execute the demo data loading job."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            demo_enabled = getattr(settings, "PLUGINS_CONFIG", {}).get("nautobot_network_provisioning", {}).get("demo_data", False)
            if not demo_enabled:
                msg = (
                    "NetAccess demo data is disabled. Enable it by setting "
                    "PLUGINS_CONFIG['nautobot_network_provisioning']['demo_data'] = true, then re-run this job."
                )
                self.logger.error(msg)
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log(msg, level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return msg

            from nautobot_network_provisioning.models import (
                ARPEntry,
                PortService,
                SwitchProfile,
                ConfigTemplate,
                ControlSetting,
                JackMapping,
                MACAddress,
                MACAddressEntry,
                MACAddressHistory,
                WorkQueueEntry,
            )
            
            overwrite = kwargs.get("overwrite_existing", False)
            data_set = kwargs.get("data_set") or getattr(settings, "PLUGINS_CONFIG", {}).get("nautobot_network_provisioning", {}).get(
                "demo_data_default_set", "full"
            )
            load_services = kwargs.get("load_services", True)
            load_profiles = kwargs.get("load_profiles", True)
            load_templates = kwargs.get("load_templates", True)
            load_controls = kwargs.get("load_controls", True)
            load_jack_mappings = kwargs.get("load_sample_jack_mappings", False)
            load_device_types = kwargs.get("load_device_types", True)
            load_graphql_queries = kwargs.get("load_graphql_queries", True)
            load_operational_data = kwargs.get("load_operational_data", True)
            load_work_queue_entries = kwargs.get("load_work_queue_entries", True)
            
            # Filter data based on selected data set
            if data_set == "minimal":
                services_to_load = [s for s in DEMO_PORT_SERVICES if s["name"] in [
                    "Access-Data", "Access-VoIP", "VoIP-Converged", "Unused-Port",
                    "Change-VLAN", "Enable-Port", "Disable-Port", "Trunk-Switch"
                ]]
                profiles_to_load = [p for p in DEMO_SWITCH_PROFILES if "Generic" in p["name"] or "9300" in p["name"]]
            elif data_set == "utility_only":
                services_to_load = [s for s in DEMO_PORT_SERVICES if s["name"] in [
                    "Change-VLAN", "Change-Voice-VLAN", "Enable-Port", "Disable-Port",
                    "Change-Description", "Clear-Config", "Unused-Port"
                ]]
                profiles_to_load = [p for p in DEMO_SWITCH_PROFILES if "Generic" in p["name"]]
            else:
                services_to_load = DEMO_PORT_SERVICES
                profiles_to_load = DEMO_SWITCH_PROFILES
            
            stats = {
                "services_created": 0,
                "services_updated": 0,
                "services_skipped": 0,
                "profiles_created": 0,
                "profiles_updated": 0,
                "profiles_skipped": 0,
                "templates_created": 0,
                "templates_updated": 0,
                "templates_skipped": 0,
                "templates_failed": 0,
                "controls_created": 0,
                "controls_updated": 0,
                "jack_mappings_created": 0,
                # New out-of-the-box demo additions
                "device_types_imported": 0,
                "locations_created": 0,
                "graphql_queries_created": 0,
                "graphql_queries_updated": 0,
                "devices_created": 0,
                "interfaces_created": 0,
                "macs_created": 0,
                "mac_entries_created": 0,
                "mac_history_created": 0,
                "arp_entries_created": 0,
                "work_queue_created": 0,
            }
            
            self.logger.info("=" * 70)
            self.logger.info("NetAccess Demo Data Loader")
            self.logger.info(f"Data Set: {data_set}")
            self.logger.info(f"Overwrite Existing: {overwrite}")
            self.logger.info("=" * 70)
            
            # =====================================================================
            # LOAD PORT SERVICES
            # =====================================================================
            if load_services:
                self.logger.info("\n[1/5] Loading Port Services...")
                
                for svc_data in services_to_load:
                    try:
                        existing = PortService.objects.filter(name=svc_data["name"]).first()
                        
                        if existing:
                            if overwrite:
                                existing.description = svc_data["description"]
                                existing.is_active = svc_data["is_active"]
                                existing.save()
                                stats["services_updated"] += 1
                                self.logger.info(f"  Updated: {svc_data['name']}")
                            else:
                                stats["services_skipped"] += 1
                        else:
                            PortService.objects.create(**svc_data)
                            stats["services_created"] += 1
                            self.logger.info(f"  Created: {svc_data['name']}")
                    except Exception as e:
                        self.logger.warning(f"  Failed to create service {svc_data['name']}: {e}")
                
                self.logger.info(
                    f"Port Services: {stats['services_created']} created, "
                    f"{stats['services_updated']} updated, "
                    f"{stats['services_skipped']} skipped"
                )
            
            # =====================================================================
            # LOAD SWITCH PROFILES
            # =====================================================================
            if load_profiles:
                self.logger.info("\n[2/5] Loading Switch Profiles...")
                
                for profile_data in profiles_to_load:
                    try:
                        existing = SwitchProfile.objects.filter(name=profile_data["name"]).first()
                        
                        if existing:
                            if overwrite:
                                existing.device_type_pattern = profile_data["device_type_pattern"]
                                existing.os_version_pattern = profile_data["os_version_pattern"]
                                existing.priority = profile_data["priority"]
                                existing.save()
                                stats["profiles_updated"] += 1
                                self.logger.info(f"  Updated: {profile_data['name']}")
                            else:
                                stats["profiles_skipped"] += 1
                        else:
                            SwitchProfile.objects.create(**profile_data)
                            stats["profiles_created"] += 1
                            self.logger.info(f"  Created: {profile_data['name']}")
                    except Exception as e:
                        self.logger.warning(f"  Failed to create profile {profile_data['name']}: {e}")
                
                self.logger.info(
                    f"Switch Profiles: {stats['profiles_created']} created, "
                    f"{stats['profiles_updated']} updated, "
                    f"{stats['profiles_skipped']} skipped"
                )
            
            # =====================================================================
            # LOAD CONFIGURATION TEMPLATES
            # =====================================================================
            if load_templates:
                self.logger.info("\n[3/5] Loading Configuration Templates...")
                
                # Filter mappings based on data set
                if data_set != "full":
                    service_names = [s["name"] for s in services_to_load]
                    profile_names = [p["name"] for p in profiles_to_load]
                    mappings_to_load = [
                        m for m in TEMPLATE_MAPPINGS 
                        if m[0] in service_names and m[1] in profile_names
                    ]
                else:
                    mappings_to_load = TEMPLATE_MAPPINGS
                
                for svc_name, profile_name, template_key, instance, version in mappings_to_load:
                    try:
                        service = PortService.objects.filter(name=svc_name).first()
                        profile = SwitchProfile.objects.filter(name=profile_name).first()
                        
                        if not service:
                            continue
                        if not profile:
                            continue
                        
                        template_text = DEMO_TEMPLATES.get(template_key, "")
                        if not template_text:
                            self.logger.warning(f"  Template key not found: {template_key}")
                            stats["templates_failed"] += 1
                            continue
                        
                        existing = ConfigTemplate.objects.filter(
                            service=service,
                            switch_profile=profile,
                            instance=instance,
                        ).first()
                        
                        if existing:
                            if overwrite:
                                existing.template_text = template_text
                                existing.version = version
                                existing.created_by = "demo_loader"
                                existing.save()
                                stats["templates_updated"] += 1
                                self.logger.info(f"  Updated: {svc_name} / {profile_name}")
                            else:
                                stats["templates_skipped"] += 1
                        else:
                            ConfigTemplate.objects.create(
                                service=service,
                                switch_profile=profile,
                                instance=instance,
                                version=version,
                                template_text=template_text,
                                created_by="demo_loader",
                            )
                            stats["templates_created"] += 1
                            self.logger.info(f"  Created: {svc_name} / {profile_name}")
                    except Exception as e:
                        self.logger.warning(f"  Failed: {svc_name}/{profile_name} - {e}")
                        stats["templates_failed"] += 1
                
                self.logger.info(
                    f"Templates: {stats['templates_created']} created, "
                    f"{stats['templates_updated']} updated, "
                    f"{stats['templates_skipped']} skipped, "
                    f"{stats['templates_failed']} failed"
                )
            
            # =====================================================================
            # LOAD CONTROL SETTINGS
            # =====================================================================
            if load_controls:
                self.logger.info("\n[4/5] Loading Control Settings...")
                
                for ctrl_data in DEMO_CONTROL_SETTINGS:
                    try:
                        existing = ControlSetting.objects.filter(name=ctrl_data["name"]).first()
                        
                        if existing:
                            if overwrite:
                                existing.value = ctrl_data["value"]
                                existing.description = ctrl_data["description"]
                                existing.save()
                                stats["controls_updated"] += 1
                                self.logger.info(f"  Updated: {ctrl_data['name']}")
                        else:
                            ControlSetting.objects.create(**ctrl_data)
                            stats["controls_created"] += 1
                            self.logger.info(f"  Created: {ctrl_data['name']}")
                    except Exception as e:
                        self.logger.warning(f"  Failed to create control {ctrl_data['name']}: {e}")
                
                self.logger.info(
                    f"Control Settings: {stats['controls_created']} created, "
                    f"{stats['controls_updated']} updated"
                )
            
            # =====================================================================
            # LOAD SAMPLE JACK MAPPINGS (if requested)
            # =====================================================================
            if load_jack_mappings:
                self.logger.info("\n[5/5] Creating Sample Jack Mappings...")
                
                buildings = Location.objects.filter(
                    location_type__name__icontains="building"
                )[:3]
                
                if not buildings.exists():
                    buildings = Location.objects.all()[:3]
                
                devices = Device.objects.filter(
                    device_type__model__icontains="C9300"
                )[:3]
                
                if not devices.exists():
                    devices = Device.objects.filter(interfaces__isnull=False).distinct()[:3]
                
                sample_jacks = [
                    ("A-101", "MDF-1"),
                    ("A-102", "MDF-1"),
                    ("B-201", "IDF-2"),
                    ("B-202", "IDF-2"),
                    ("C-301", "IDF-3"),
                ]
                
                for i, device in enumerate(devices):
                    if i >= len(buildings):
                        break
                        
                    building = buildings[i] if buildings else None
                    interfaces = Interface.objects.filter(device=device)[:5]
                    
                    for j, interface in enumerate(interfaces):
                        if j >= len(sample_jacks):
                            break
                        
                        jack_id, comm_room = sample_jacks[j]
                        
                        try:
                            existing = JackMapping.objects.filter(
                                building=building,
                                comm_room=comm_room,
                                jack=jack_id,
                            ).first()
                            
                            if not existing and building:
                                JackMapping.objects.create(
                                    building=building,
                                    comm_room=comm_room,
                                    jack=jack_id,
                                    device=device,
                                    interface=interface,
                                )
                                stats["jack_mappings_created"] += 1
                                self.logger.info(
                                    f"  Created: {building.name}/{comm_room}/{jack_id} -> "
                                    f"{device.name}/{interface.name}"
                                )
                        except Exception as e:
                            self.logger.warning(f"  Failed to create mapping: {e}")
                
                self.logger.info(f"Jack Mappings: {stats['jack_mappings_created']} created")
            else:
                self.logger.info("\n[5/5] Skipping Jack Mappings (not selected)")

            # =====================================================================
            # OUT-OF-THE-BOX DEMO ADDITIONS
            # =====================================================================
            # These additions provide a working experience immediately after loading:
            # - Saved GraphQL queries for Template IDE
            # - Optional import of real DeviceTypes from nautobot/devicetype-library (GitHub)
            # - Demo devices + interfaces
            # - MAC/ARP tables + history
            # - Sample Work Queue entries

            # ----------------------------
            # Saved GraphQL Queries
            # ----------------------------
            if load_graphql_queries:
                queries = [
                    {
                        "name": "NetAccess: Device for Template",
                        "query": """query DeviceForTemplate($device_id: ID!) {
  device(id: $device_id) {
    name
    platform { name manufacturer { name } }
    primary_ip4 { address }
    location { name parent { name } }
    interfaces {
      name
      enabled
      description
      mode
      untagged_vlan { vid name }
      tagged_vlans { vid name }
    }
  }
}
""",
                    },
                    {
                        "name": "NetAccess: Location Hierarchy",
                        "query": """query LocationHierarchy {
  locations {
    name
    location_type { name }
    parent { name }
    devices { name device_type { model } }
  }
}
""",
                    },
                ]

                for q in queries:
                    _, created = GraphQLQuery.objects.update_or_create(
                        name=q["name"],
                        defaults={"query": q["query"], "variables": {}},
                    )
                    if created:
                        stats["graphql_queries_created"] += 1
                    else:
                        stats["graphql_queries_updated"] += 1

            # ----------------------------
            # DeviceTypes from GitHub
            # ----------------------------
            imported_device_types: list[DeviceType] = []
            if load_device_types:
                imported_device_types = import_device_types(
                    refs=DEFAULT_DEVICE_TYPES,
                    overwrite_existing=overwrite,
                    log=self.logger.info,
                )
                stats["device_types_imported"] = len(imported_device_types)

            # ----------------------------
            # Demo locations, platforms, versions, devices, and interfaces
            # ----------------------------
            active_status = Status.objects.filter(name__iexact="Active").first() or Status.objects.filter(
                name__icontains="active"
            ).first()
            device_role, _ = Role.objects.get_or_create(
                name="Switch",
                defaults={"description": "Demo switch role", "color": "9e9e9e", "weight": 1000},
            )

            campus_type, _ = LocationType.objects.get_or_create(name="Campus", defaults={"description": "Campus"})
            building_type, _ = LocationType.objects.get_or_create(
                name="Building", defaults={"description": "Building", "parent": campus_type}
            )

            campus, created = Location.objects.get_or_create(
                name="Demo Campus",
                location_type=campus_type,
                defaults={"status": active_status} if active_status else {},
            )
            if created:
                stats["locations_created"] += 1

            main_building, created = Location.objects.get_or_create(
                name="Main Building",
                location_type=building_type,
                defaults={"status": active_status, "parent": campus} if active_status else {"parent": campus},
            )
            if created:
                stats["locations_created"] += 1

            research_building, created = Location.objects.get_or_create(
                name="Research Building",
                location_type=building_type,
                defaults={"status": active_status, "parent": campus} if active_status else {"parent": campus},
            )
            if created:
                stats["locations_created"] += 1

            cisco_mfr, _ = Manufacturer.objects.get_or_create(name="Cisco")
            arista_mfr, _ = Manufacturer.objects.get_or_create(name="Arista")

            ios_platform, _ = Platform.objects.get_or_create(
                name="Cisco IOS",
                defaults={"manufacturer": cisco_mfr, "description": "Cisco IOS"},
            )
            nxos_platform, _ = Platform.objects.get_or_create(
                name="Cisco NX-OS",
                defaults={"manufacturer": cisco_mfr, "description": "Cisco NX-OS"},
            )
            eos_platform, _ = Platform.objects.get_or_create(
                name="Arista EOS",
                defaults={"manufacturer": arista_mfr, "description": "Arista EOS"},
            )

            def ensure_software_version(platform: Platform, version_text: str):
                """Create or get a SoftwareVersion, handling status requirement."""
                SoftwareVersion = Platform._meta.apps.get_model("dcim", "SoftwareVersion")
                fields = {f.name for f in SoftwareVersion._meta.fields}
                
                # Build defaults with required fields
                defaults: dict[str, object] = {"platform": platform}
                lookup: dict[str, object] = {"platform": platform}
                
                if "version" in fields:
                    lookup["version"] = version_text
                    defaults["version"] = version_text
                if "alias" in fields:
                    lookup.setdefault("alias", version_text)
                    defaults.setdefault("alias", version_text)
                
                # SoftwareVersion requires a status - use active_status from outer scope
                if "status" in fields and active_status:
                    defaults["status"] = active_status
                
                obj, _ = SoftwareVersion.objects.get_or_create(**lookup, defaults=defaults)
                return obj

            ios_ver = ensure_software_version(ios_platform, "17.9.4")
            nxos_ver = ensure_software_version(nxos_platform, "10.1(1)")
            eos_ver = ensure_software_version(eos_platform, "4.31.2F")

            def pick_device_type(manufacturer: Manufacturer) -> DeviceType:
                dt = next((d for d in imported_device_types if d.manufacturer_id == manufacturer.id), None)
                if dt:
                    return dt
                dt, _ = DeviceType.objects.get_or_create(
                    manufacturer=manufacturer,
                    model=f"{manufacturer.name} Demo Switch",
                    defaults={"u_height": 1, "is_full_depth": False},
                )
                return dt

            def ensure_device(name: str, location: Location, platform: Platform, manufacturer: Manufacturer) -> Device:
                dt = pick_device_type(manufacturer)
                defaults: dict[str, object] = {
                    "device_type": dt,
                    "role": device_role,
                    "location": location,
                    "platform": platform,
                }
                if active_status:
                    defaults["status"] = active_status
                device, created = Device.objects.get_or_create(name=name, defaults=defaults)
                if created:
                    stats["devices_created"] += 1
                return device

            access1 = ensure_device("ACCESS-1", research_building, ios_platform, cisco_mfr)
            access2 = ensure_device("ACCESS-2", research_building, ios_platform, cisco_mfr)
            ensure_device("CORE-1", main_building, nxos_platform, cisco_mfr)
            ensure_device("CORE-2", main_building, nxos_platform, cisco_mfr)
            ensure_device("LEAF-1", main_building, eos_platform, arista_mfr)

            def ensure_interfaces(device: Device, *, count: int = 24) -> list[Interface]:
                existing = list(Interface.objects.filter(device=device).order_by("name"))
                if len(existing) >= count:
                    return existing[:count]

                template_names = list(
                    InterfaceTemplate.objects.filter(device_type=device.device_type)
                    .order_by("name")
                    .values_list("name", flat=True)
                )
                names = template_names[:count] if template_names else [f"Ethernet1/{i}" for i in range(1, count + 1)]

                created_ifaces: list[Interface] = []
                for name in names:
                    iface, created = Interface.objects.get_or_create(
                        device=device,
                        name=name,
                        defaults={"enabled": True},
                    )
                    if created:
                        stats["interfaces_created"] += 1
                    created_ifaces.append(iface)
                return created_ifaces

            access_ifaces = ensure_interfaces(access1, count=24) + ensure_interfaces(access2, count=24)

            # Create platform-specific templates that render in the IDE immediately
            service_access_data = PortService.objects.filter(name="Access-Data").first()
            service_access_voip = PortService.objects.filter(name="Access-VoIP").first()
            service_trunk = PortService.objects.filter(name="Trunk-Switch").first()

            # Platform-specific template strings with proper newlines
            IOS_ACCESS_TEMPLATE = """!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} {{ service_name | default("Data") }}
 switchport mode access
 switchport access vlan {{ vlan | default(100) }}
 switchport voice vlan {{ voice_vlan | default(200) }}
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""
            NXOS_ACCESS_TEMPLATE = """!
interface {{ interface_name }}
  description {{ building_name }}-{{ comm_room }}-{{ jack }} {{ service_name | default("Data") }}
  switchport
  switchport mode access
  switchport access vlan {{ vlan | default(100) }}
  switchport voice vlan {{ voice_vlan | default(200) }}
  spanning-tree port type edge
  spanning-tree bpduguard enable
  no shutdown
!
"""
            EOS_ACCESS_TEMPLATE = """!
interface {{ interface_name }}
   description {{ building_name }}-{{ comm_room }}-{{ jack }} {{ service_name | default("Data") }}
   switchport mode access
   switchport access vlan {{ vlan | default(100) }}
   switchport voice vlan {{ voice_vlan | default(200) }}
   spanning-tree portfast
   spanning-tree bpduguard enable
   no shutdown
!
"""
            IOS_VOIP_TEMPLATE = """!
interface {{ interface_name }}
 description {{ building_name }}-{{ comm_room }}-{{ jack }} VoIP
 switchport mode access
 switchport access vlan {{ data_vlan | default(100) }}
 switchport voice vlan {{ voice_vlan | default(200) }}
 authentication host-mode multi-domain
 authentication port-control auto
 mab
 dot1x pae authenticator
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
"""
            NXOS_VOIP_TEMPLATE = """!
interface {{ interface_name }}
  description {{ building_name }}-{{ comm_room }}-{{ jack }} VoIP
  switchport
  switchport mode access
  switchport access vlan {{ data_vlan | default(100) }}
  switchport voice vlan {{ voice_vlan | default(200) }}
  spanning-tree port type edge
  spanning-tree bpduguard enable
  no shutdown
!
"""
            EOS_VOIP_TEMPLATE = """!
interface {{ interface_name }}
   description {{ building_name }}-{{ comm_room }}-{{ jack }} VoIP
   switchport mode access
   switchport access vlan {{ data_vlan | default(100) }}
   switchport voice vlan {{ voice_vlan | default(200) }}
   spanning-tree portfast
   spanning-tree bpduguard enable
   no shutdown
!
"""
            IOS_TRUNK_TEMPLATE = """!
interface {{ interface_name }}
 description TRUNK-TO-{{ neighbor_device | default("UPLINK") }}
 switchport mode trunk
 switchport trunk native vlan {{ native_vlan | default(1) }}
 switchport trunk allowed vlan {{ allowed_vlans | default("10,100,200,300") }}
 spanning-tree portfast trunk
 no shutdown
!
"""
            NXOS_TRUNK_TEMPLATE = """!
interface {{ interface_name }}
  description TRUNK-TO-{{ neighbor_device | default("UPLINK") }}
  switchport
  switchport mode trunk
  switchport trunk native vlan {{ native_vlan | default(1) }}
  switchport trunk allowed vlan {{ allowed_vlans | default("10,100,200,300") }}
  spanning-tree port type edge trunk
  no shutdown
!
"""
            EOS_TRUNK_TEMPLATE = """!
interface {{ interface_name }}
   description TRUNK-TO-{{ neighbor_device | default("UPLINK") }}
   switchport mode trunk
   switchport trunk native vlan {{ native_vlan | default(1) }}
   switchport trunk allowed vlan {{ allowed_vlans | default("10,100,200,300") }}
   spanning-tree portfast trunk
   no shutdown
!
"""
            templates_by_service: dict[PortService, dict[Platform, str]] = {}
            if service_access_data:
                templates_by_service[service_access_data] = {
                    ios_platform: IOS_ACCESS_TEMPLATE,
                    nxos_platform: NXOS_ACCESS_TEMPLATE,
                    eos_platform: EOS_ACCESS_TEMPLATE,
                }
            if service_access_voip:
                templates_by_service[service_access_voip] = {
                    ios_platform: IOS_VOIP_TEMPLATE,
                    nxos_platform: NXOS_VOIP_TEMPLATE,
                    eos_platform: EOS_VOIP_TEMPLATE,
                }
            if service_trunk:
                templates_by_service[service_trunk] = {
                    ios_platform: IOS_TRUNK_TEMPLATE,
                    nxos_platform: NXOS_TRUNK_TEMPLATE,
                    eos_platform: EOS_TRUNK_TEMPLATE,
                }

            if load_templates:
                for service, platform_map in templates_by_service.items():
                    for platform_obj, template_text in platform_map.items():
                        manufacturer_obj = platform_obj.manufacturer
                        tpl, created = ConfigTemplate.objects.get_or_create(
                            service=service,
                            manufacturer=manufacturer_obj,
                            platform=platform_obj,
                            version=1,
                            defaults={
                                "template_text": template_text,
                                "created_by": "demo_loader",
                                "is_active": True,
                                "effective_date": timezone.now().date(),
                            },
                        )
                        if created:
                            stats["templates_created"] += 1
                        elif overwrite:
                            tpl.template_text = template_text
                            tpl.created_by = "demo_loader"
                            tpl.is_active = True
                            tpl.save()
                            stats["templates_updated"] += 1

                        try:
                            if platform_obj == ios_platform:
                                tpl.software_versions.add(ios_ver)
                            elif platform_obj == nxos_platform:
                                tpl.software_versions.add(nxos_ver)
                            elif platform_obj == eos_platform:
                                tpl.software_versions.add(eos_ver)
                        except Exception:
                            pass

            # If the user didn't opt into jack mappings earlier, still create a reasonable default set for the demo devices.
            if not load_jack_mappings and access_ifaces:
                comm_rooms = ["MDF-1", "IDF-1", "IDF-2"]
                for idx, iface in enumerate(access_ifaces, start=1):
                    comm_room = comm_rooms[(idx - 1) % len(comm_rooms)]
                    jack = f"A-{idx:03d}"
                    _, created = JackMapping.objects.get_or_create(
                        building=research_building,
                        comm_room=comm_room,
                        jack=jack,
                        defaults={
                            "device": iface.device,
                            "interface": iface,
                            "description": f"Demo jack mapping for {iface.device.name}:{iface.name}",
                            "is_active": True,
                        },
                    )
                    if created:
                        stats["jack_mappings_created"] += 1

            # ----------------------------
            # Operational data (MAC/ARP/history)
            # ----------------------------
            if load_operational_data and access_ifaces:
                self.logger.info("\n[6/7] Creating operational demo data (MAC/ARP/History)...")
                
                vendor_ouis = [
                    ("00:1B:54", "Cisco"),
                    ("00:1C:73", "Dell"),
                    ("3C:D9:2B", "Apple"),
                    ("00:25:90", "HP"),
                    ("00:50:56", "VMware"),
                    ("F4:5C:89", "Intel"),
                ]

                def rand_mac() -> tuple[str, str]:
                    oui, vendor = random.choice(vendor_ouis)
                    suffix = ":".join(f"{random.randint(0, 255):02X}" for _ in range(3))
                    return f"{oui}:{suffix}", vendor

                now = timezone.now()
                first_seen_base = now - datetime.timedelta(days=30)
                mac_target = 600 if data_set == "full" else 250

                # Generate unique MAC addresses
                mac_addresses_generated = set()
                mac_objs = []
                attempts = 0
                max_attempts = mac_target * 3  # Allow for some collisions
                
                while len(mac_objs) < mac_target and attempts < max_attempts:
                    mac_str, vendor = rand_mac()
                    if mac_str not in mac_addresses_generated:
                        mac_addresses_generated.add(mac_str)
                        mac_objs.append(
                            MACAddress(
                                address=mac_str,
                                vendor=vendor,
                                mac_type=MACAddress.MACTypeChoices.ENDPOINT,
                                first_seen=first_seen_base + datetime.timedelta(days=random.randint(0, 29)),
                                last_seen=now - datetime.timedelta(hours=random.randint(0, 72)),
                            )
                        )
                    attempts += 1
                
                self.logger.info(f"  Generated {len(mac_objs)} unique MAC addresses")
                
                # Bulk create MACs
                MACAddress.objects.bulk_create(mac_objs, ignore_conflicts=True)
                
                # Fetch the persisted MACs by the addresses we generated
                persisted_macs = list(
                    MACAddress.objects.filter(address__in=list(mac_addresses_generated))
                )
                self.logger.info(f"  Persisted {len(persisted_macs)} MAC addresses to database")

                if not persisted_macs:
                    self.logger.warning("  No MAC addresses were created - skipping entries/history")
                else:
                    entries = []
                    histories = []
                    arps = []
                    vlan_pool = [10, 100, 200, 300]
                    subnet_pool = [ipaddress.ip_network("10.10.0.0/16"), ipaddress.ip_network("10.20.0.0/16")]
                    
                    # Track used IPs to avoid conflicts
                    used_ips = set()

                    for mac in persisted_macs:
                        iface = random.choice(access_ifaces)
                        vlan = random.choice(vlan_pool)
                        mac.last_device = iface.device
                        mac.last_interface = iface
                        mac.last_vlan = vlan
                        mac.save(update_fields=["last_device", "last_interface", "last_vlan"])

                        entries.append(
                            MACAddressEntry(
                                mac_address=mac,
                                device=iface.device,
                                interface=iface,
                                vlan=vlan,
                                entry_type=MACAddressEntry.EntryTypeChoices.DYNAMIC,
                            )
                        )

                        # Create 3 historical sightings per MAC
                        for _ in range(3):
                            hist_iface = random.choice(access_ifaces)
                            start = first_seen_base + datetime.timedelta(days=random.randint(0, 28))
                            end = start + datetime.timedelta(hours=random.randint(1, 72))
                            histories.append(
                                MACAddressHistory(
                                    mac_address=mac,
                                    device=hist_iface.device,
                                    interface=hist_iface,
                                    vlan=random.choice(vlan_pool),
                                    entry_type="dynamic",
                                    first_seen=start,
                                    last_seen=min(end, now),
                                    sighting_count=random.randint(1, 20),
                                )
                            )

                        # Generate unique IP for ARP entry
                        net = random.choice(subnet_pool)
                        ip_int = random.randint(10, 65000)
                        ip_addr = str(net.network_address + ip_int)
                        
                        # Retry if IP already used (for unique constraint)
                        retries = 0
                        while ip_addr in used_ips and retries < 10:
                            ip_int = random.randint(10, 65000)
                            ip_addr = str(net.network_address + ip_int)
                            retries += 1
                        
                        if ip_addr not in used_ips:
                            used_ips.add(ip_addr)
                            arps.append(
                                ARPEntry(
                                    mac_address=mac,
                                    ip_address=ip_addr,
                                    device=iface.device,
                                    interface=iface,
                                    vrf="default",
                                    entry_type=ARPEntry.EntryTypeChoices.DYNAMIC,
                                )
                            )

                    # Bulk create all related entries
                    self.logger.info(f"  Creating {len(entries)} MAC entries...")
                    MACAddressEntry.objects.bulk_create(entries, ignore_conflicts=True)
                    
                    self.logger.info(f"  Creating {len(histories)} MAC history records...")
                    MACAddressHistory.objects.bulk_create(histories, ignore_conflicts=True)
                    
                    self.logger.info(f"  Creating {len(arps)} ARP entries...")
                    ARPEntry.objects.bulk_create(arps, ignore_conflicts=True)

                    stats["macs_created"] = len(persisted_macs)
                    stats["mac_entries_created"] = len(entries)
                    stats["mac_history_created"] = len(histories)
                    stats["arp_entries_created"] = len(arps)
                    
                    self.logger.info(
                        f"  Operational data: {stats['macs_created']} MACs, "
                        f"{stats['mac_entries_created']} entries, "
                        f"{stats['mac_history_created']} history, "
                        f"{stats['arp_entries_created']} ARPs"
                    )

            # ----------------------------
            # Work queue entries
            # ----------------------------
            if load_work_queue_entries and access_ifaces:
                self.logger.info("\n[7/7] Creating sample Work Queue entries...")
                
                service = PortService.objects.filter(name="Access-Data").first() or PortService.objects.first()
                template = None
                if service:
                    # Try to find a platform-specific template first
                    template = (
                        ConfigTemplate.objects.filter(service=service, platform=ios_platform, is_active=True).first()
                        or ConfigTemplate.objects.filter(service=service, is_active=True).first()
                    )

                if service and template:
                    self.logger.info(f"  Using service: {service.name}")
                    self.logger.info(f"  Using template: {template}")
                    
                    base_time = timezone.now()
                    for i in range(5):
                        iface = access_ifaces[i]
                        _, created = WorkQueueEntry.objects.get_or_create(
                            device=iface.device,
                            interface=iface,
                            service=service,
                            template=template,
                            scheduled_time=base_time + datetime.timedelta(minutes=10 * i),
                            defaults={
                                "status": WorkQueueEntry.StatusChoices.PENDING,
                                "requested_by": "demo_loader",
                                "vlan": 100,
                                "status_message": "Demo pending entry",
                                "building": research_building,
                                "comm_room": "IDF-1",
                                "jack": f"A-{i+1:03d}",
                            },
                        )
                        if created:
                            stats["work_queue_created"] += 1
                    
                    self.logger.info(f"  Work Queue: {stats['work_queue_created']} entries created")
                else:
                    self.logger.warning("  No service or template found - skipping work queue entries")
            else:
                self.logger.info("\n[7/7] Skipping Work Queue entries (not selected or no interfaces)")
            
            # =====================================================================
            # SUMMARY
            # =====================================================================
            self.logger.info("\n" + "=" * 70)
            self.logger.info("Demo Data Loading Complete!")
            self.logger.info("=" * 70)
            
            total_created = (
                stats['services_created'] + stats['profiles_created'] + 
                stats['templates_created'] + stats['controls_created'] +
                stats['jack_mappings_created']
            )
            total_updated = (
                stats['services_updated'] + stats['profiles_updated'] + 
                stats['templates_updated'] + stats['controls_updated']
            )
            
            self.logger.info(f"""
Summary:
  Port Services:     {stats['services_created']:3d} created, {stats['services_updated']:3d} updated
  Switch Profiles:   {stats['profiles_created']:3d} created, {stats['profiles_updated']:3d} updated  
  Config Templates:  {stats['templates_created']:3d} created, {stats['templates_updated']:3d} updated, {stats['templates_failed']:3d} failed
  Control Settings:  {stats['controls_created']:3d} created, {stats['controls_updated']:3d} updated
  Jack Mappings:     {stats['jack_mappings_created']:3d} created
  DeviceTypes:       {stats['device_types_imported']:3d} imported (GitHub)
  Demo Devices:      {stats['devices_created']:3d} created, {stats['interfaces_created']:3d} interfaces
  MAC Tracking:      {stats['macs_created']:3d} MACs, {stats['mac_entries_created']:3d} CAM entries, {stats['mac_history_created']:3d} history
  ARP Table:         {stats['arp_entries_created']:3d} entries
  Work Queue:        {stats['work_queue_created']:3d} entries
  GraphQL Queries:   {stats['graphql_queries_created']:3d} created, {stats['graphql_queries_updated']:3d} updated
  ─────────────────────────────────────────────
  Total:             {total_created:3d} created, {total_updated:3d} updated

Next Steps:
  1. Browse Port Services at: /plugins/netaccess/port-services/
  2. Browse Switch Profiles at: /plugins/netaccess/switch-profiles/
  3. Browse & Edit Config Templates at: /plugins/netaccess/config-templates/
  4. Create Work Queue entries to schedule configuration changes
  5. Run the Work Queue Processor job to apply configurations

All templates are stored in the database and can be edited directly in the GUI!
""")
            
            summary = (
                f"Demo data loaded: {total_created} records created, {total_updated} updated. "
                f"DeviceTypes imported: {stats['device_types_imported']}, "
                f"MACs: {stats['macs_created']}, ARP: {stats['arp_entries_created']}."
            )
            
            # Mark job as SUCCESS
            self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
            self.job_result.log(summary, level_choice=LogLevelChoices.LOG_INFO)
            self.job_result.save()
            
            return summary

        except Exception as e:
            error_message = f"Job failed with error: {str(e)}"
            self.logger.error(error_message)
            self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
            self.job_result.log(error_message, level_choice=LogLevelChoices.LOG_ERROR)
            self.job_result.save()
            raise


# Register the job
register_jobs(LoadDemoData)
