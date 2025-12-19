"""Demo data setup job.

Creates an end-to-end sample dataset so the UI has meaningful examples:
- Provider + ProviderConfig
- Manufacturer/Platform/Location/DeviceType/Device (minimal demo target)
- TaskDefinitions + TaskImplementations
- Workflow + WorkflowSteps (including Approval step)
- RequestForm + RequestFormFields (including map_to and conditional field)

Designed to be idempotent and safe to run multiple times.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from nautobot.apps.jobs import Job

from nautobot_network_provisioning.models import (
    Execution,
    Provider,
    ProviderConfig,
    RequestForm,
    RequestFormField,
    TaskDefinition,
    TaskImplementation,
    Workflow,
    WorkflowStep,
)


def _plugin_demo_enabled() -> bool:
    cfg = (getattr(settings, "PLUGINS_CONFIG", {}) or {}).get("nautobot_network_provisioning", {}) or {}
    return bool(cfg.get("demo_data", False))


def _get_or_create_named_with_optional_slug(model, *, name: str, slug: str):  # noqa: ANN001
    """Get/create a model that may or may not have a `slug` field (varies by Nautobot version)."""

    try:
        model._meta.get_field("slug")
        obj, _ = model.objects.get_or_create(name=name, defaults={"slug": slug})
        return obj
    except Exception:  # noqa: BLE001
        obj, _ = model.objects.get_or_create(name=name)
        return obj


def _filter_defaults_for_model(model, defaults: dict):  # noqa: ANN001
    """Remove keys from defaults that don't exist as concrete model fields."""

    field_names = {f.name for f in model._meta.fields}
    return {k: v for k, v in (defaults or {}).items() if k in field_names}


class DemoDataSetup(Job):
    """Load demo data for a "first look" experience."""

    class Meta:  # noqa: D106
        name = "Demo Data Setup"
        description = "Create demo Tasks/Workflows/Request Forms/Providers (+ a demo Device) for a complete example UI."

    def run(self, force: bool = False):  # noqa: D102
        if not force and not _plugin_demo_enabled():
            return (
                "Demo data is disabled. Enable it by setting "
                "PLUGINS_CONFIG['nautobot_network_provisioning']['demo_data']=True "
                "or run this job with force=True."
            )

        # ---------------------------
        # Core Nautobot objects
        # ---------------------------
        from nautobot.dcim.models import Device, DeviceType, Manufacturer, Platform, Interface, FrontPort, RearPort, Cable
        from nautobot.dcim.models import Location, LocationType
        from nautobot.ipam.models import VLAN
        from nautobot.extras.models import Role, Status, GitRepository, Tag

        ct_device = ContentType.objects.get(app_label="dcim", model="device")

        # Status + Role used by Device (ensure content-type bindings exist)
        status_active = Status.objects.filter(name="Active").first()
        if status_active is None:
            status_active = _get_or_create_named_with_optional_slug(Status, name="Active", slug="active")
        if not status_active.content_types.filter(pk=ct_device.pk).exists():
            status_active.content_types.add(ct_device)

        role_demo = Role.objects.filter(name="Demo").first()
        if role_demo is None:
            role_demo = _get_or_create_named_with_optional_slug(Role, name="Demo", slug="demo")
        if not role_demo.content_types.filter(pk=ct_device.pk).exists():
            role_demo.content_types.add(ct_device)

        ct_vlan = ContentType.objects.get(app_label="ipam", model="vlan")

        loc_type, _ = LocationType.objects.get_or_create(name="Site", defaults={"nestable": True})
        if not loc_type.content_types.filter(pk=ct_vlan.pk).exists():
            loc_type.content_types.add(ct_vlan)

        bldg_type, _ = LocationType.objects.get_or_create(name="Building", defaults={"parent": loc_type, "nestable": True})
        if not bldg_type.content_types.filter(pk=ct_vlan.pk).exists():
            bldg_type.content_types.add(ct_vlan)

        room_type, _ = LocationType.objects.get_or_create(name="Room", defaults={"parent": bldg_type, "nestable": True})

        demo_loc, _ = Location.objects.get_or_create(
            name="Demo HQ",
            defaults={"location_type": loc_type, "status": status_active},
        )
        bldg_1, _ = Location.objects.get_or_create(
            name="Building 1",
            defaults={"location_type": bldg_type, "parent": demo_loc, "status": status_active},
        )
        room_101, _ = Location.objects.get_or_create(
            name="Room 101",
            defaults={"location_type": room_type, "parent": bldg_1, "status": status_active},
        )

        # ---------------------------
        # IPAM Data Model
        # ---------------------------
        tag_data, _ = Tag.objects.get_or_create(name="Service: Data", defaults=_filter_defaults_for_model(Tag, {"slug": "service-data", "color": "0000ff"}))
        tag_voice, _ = Tag.objects.get_or_create(name="Service: Voice", defaults=_filter_defaults_for_model(Tag, {"slug": "service-voice", "color": "00ff00"}))
        tag_guest, _ = Tag.objects.get_or_create(name="Service: Guest", defaults=_filter_defaults_for_model(Tag, {"slug": "service-guest", "color": "888888"}))

        vlan_data, _ = VLAN.objects.get_or_create(
            vid=100,
            name="Data-VLAN-100",
            defaults={"status": status_active}
        )
        vlan_data.tags.add(tag_data)
        vlan_data.locations.add(bldg_1)

        vlan_voice, _ = VLAN.objects.get_or_create(
            vid=200,
            name="Voice-VLAN-200",
            defaults={"status": status_active}
        )
        vlan_voice.tags.add(tag_voice)
        vlan_voice.locations.add(bldg_1)

        vlan_guest, _ = VLAN.objects.get_or_create(
            vid=300,
            name="Guest-Wifi-300",
            defaults={"status": status_active}
        )
        vlan_guest.tags.add(tag_guest)
        vlan_guest.locations.add(bldg_1)
        
        # Manufacturers & Platforms
        cisco, _ = Manufacturer.objects.get_or_create(
            name="Cisco",
            defaults=_filter_defaults_for_model(Manufacturer, {"slug": "cisco"})
        )
        arista, _ = Manufacturer.objects.get_or_create(
            name="Arista",
            defaults=_filter_defaults_for_model(Manufacturer, {"slug": "arista"})
        )
        
        iosxe, _ = Platform.objects.get_or_create(
            name="Cisco IOS-XE",
            defaults=_filter_defaults_for_model(Platform, {
                "manufacturer": cisco,
                "slug": "cisco-ios-xe",
                "napalm_driver": "ios"
            })
        )
        eos, _ = Platform.objects.get_or_create(
            name="Arista EOS",
            defaults=_filter_defaults_for_model(Platform, {
                "manufacturer": arista,
                "slug": "arista-eos",
                "napalm_driver": "eos"
            })
        )

        # Demo Devices
        dt_cisco, _ = DeviceType.objects.get_or_create(
            manufacturer=cisco,
            model="C9300-48P",
            defaults=_filter_defaults_for_model(DeviceType, {"slug": "c9300-48p", "u_height": 1})
        )
        dt_arista, _ = DeviceType.objects.get_or_create(
            manufacturer=arista,
            model="DCS-7050SX",
            defaults=_filter_defaults_for_model(DeviceType, {"slug": "dcs-7050sx", "u_height": 1})
        )

        device_cisco, _ = Device.objects.get_or_create(
            name="cisco-sw-01",
            defaults={
                "device_type": dt_cisco,
                "status": status_active,
                "role": role_demo,
                "location": demo_loc,
                "platform": iosxe,
            },
        )
        device_arista, _ = Device.objects.get_or_create(
            name="arista-sw-01",
            defaults={
                "device_type": dt_arista,
                "status": status_active,
                "role": role_demo,
                "location": demo_loc,
                "platform": eos,
            },
        )

        # ---------------------------
        # Physical Connectivity Demo
        # ---------------------------
        dt_jack, _ = DeviceType.objects.get_or_create(
            manufacturer=cisco,
            model="Wall Jack",
            defaults=_filter_defaults_for_model(DeviceType, {"slug": "wall-jack", "u_height": 0})
        )
        dt_pp, _ = DeviceType.objects.get_or_create(
            manufacturer=cisco,
            model="Patch Panel 48",
            defaults=_filter_defaults_for_model(DeviceType, {"slug": "patch-panel-48", "u_height": 1})
        )

        # Create multiple rooms and jacks
        room_102, _ = Location.objects.get_or_create(
            name="Room 102",
            defaults={"location_type": room_type, "parent": bldg_1, "status": status_active},
        )

        jacks_data = [
            ("Jack-101-A", room_101),
            ("Jack-101-B", room_101),
            ("Jack-102-A", room_102),
            ("Jack-102-B", room_102),
        ]

        first_jack_rear = None
        for jack_name, room_loc in jacks_data:
            jack_dev, _ = Device.objects.get_or_create(
                name=jack_name,
                defaults={
                    "device_type": dt_jack,
                    "status": status_active,
                    "role": role_demo,
                    "location": room_loc,
                }
            )
            # Add ports for each jack
            jr, _ = RearPort.objects.get_or_create(device=jack_dev, name="Jack", defaults={"type": "8p8c", "positions": 1})
            jf, _ = FrontPort.objects.get_or_create(device=jack_dev, name="Jack", defaults={"type": "8p8c", "rear_port": jr, "rear_port_position": 1})
            if not first_jack_rear:
                first_jack_rear = jr

        pp_device, _ = Device.objects.get_or_create(
            name="PP-01",
            defaults={
                "device_type": dt_pp,
                "status": status_active,
                "role": role_demo,
                "location": bldg_1,
            }
        )

        # Ports for connectivity
        sw_port, _ = Interface.objects.get_or_create(device=device_cisco, name="GigabitEthernet1/0/1", defaults={"status": status_active, "type": "1000base-t"})
        pp_rear, _ = RearPort.objects.get_or_create(device=pp_device, name="Port 1", defaults={"type": "8p8c", "positions": 1})
        pp_front, _ = FrontPort.objects.get_or_create(device=pp_device, name="Port 1", defaults={"type": "8p8c", "rear_port": pp_rear, "rear_port_position": 1})

        # Cables
        if first_jack_rear and not Cable.objects.filter(
            termination_a_type=ContentType.objects.get_for_model(first_jack_rear),
            termination_a_id=first_jack_rear.pk
        ).exists() and not Cable.objects.filter(
            termination_b_type=ContentType.objects.get_for_model(pp_rear),
            termination_b_id=pp_rear.pk
        ).exists():
             Cable.objects.create(
                 status=status_active,
                 termination_a_type=ContentType.objects.get_for_model(first_jack_rear),
                 termination_a_id=first_jack_rear.pk,
                 termination_b_type=ContentType.objects.get_for_model(pp_rear),
                 termination_b_id=pp_rear.pk,
             )
        if not Cable.objects.filter(
            termination_a_type=ContentType.objects.get_for_model(pp_front),
            termination_a_id=pp_front.pk
        ).exists() and not Cable.objects.filter(
            termination_b_type=ContentType.objects.get_for_model(sw_port),
            termination_b_id=sw_port.pk
        ).exists():
             Cable.objects.create(
                 status=status_active,
                 termination_a_type=ContentType.objects.get_for_model(pp_front),
                 termination_a_id=pp_front.pk,
                 termination_b_type=ContentType.objects.get_for_model(sw_port),
                 termination_b_id=sw_port.pk,
             )

        # ---------------------------
        # Git Repositories
        # ---------------------------
        demo_repo, _ = GitRepository.objects.get_or_create(
            name="Automation Catalog",
            defaults={
                "remote_url": "https://github.com/nautobot/devicetype-library.git",
                "branch": "main",
                "provided_contents": [
                    "nautobot_network_provisioning.taskimplementation",
                    "nautobot_network_provisioning.workflow"
                ]
            }
        )

        # ---------------------------
        # Providers
        # ---------------------------
        napalm_provider, _ = Provider.objects.get_or_create(
            name="napalm_cli",
            defaults={
                "driver_class": "nautobot_network_provisioning.services.providers.napalm_cli.NapalmCLIProvider",
                "description": "Demo NAPALM provider.",
                "capabilities": ["render", "diff", "apply"],
                "enabled": True,
            },
        )
        napalm_provider.supported_platforms.add(iosxe, eos)

        napalm_cfg, _ = ProviderConfig.objects.get_or_create(
            provider=napalm_provider,
            name="Default NAPALM",
            defaults={"enabled": True, "settings": {}},
        )
        napalm_cfg.scope_locations.add(demo_loc)

        # ---------------------------
        # Task Definitions (Service Catalog)
        # ---------------------------
        task_vlan, _ = TaskDefinition.objects.get_or_create(
            slug="configure-vlan",
            defaults={
                "name": "Configure VLAN",
                "description": "Create or update a VLAN on the device.",
                "category": "Network Infrastructure",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "vlan_id": {"type": "integer", "minimum": 1, "maximum": 4094},
                        "vlan_name": {"type": "string"}
                    },
                    "required": ["vlan_id"]
                }
            },
        )

        service_voice, _ = TaskDefinition.objects.get_or_create(
            slug="voice-service",
            defaults={
                "name": "Voice Service",
                "description": "Provision a port for a VoIP Phone.",
                "category": "Service Catalog",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "jack_id": {"type": "string"},
                    }
                }
            },
        )

        service_data, _ = TaskDefinition.objects.get_or_create(
            slug="data-service",
            defaults={
                "name": "Data Service",
                "description": "Provision a port for standard PC/Laptop data access.",
                "category": "Service Catalog",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "jack_id": {"type": "string"},
                    }
                }
            },
        )

        task_snmp, _ = TaskDefinition.objects.get_or_create(
            slug="configure-snmp",
            defaults={
                "name": "Configure SNMP",
                "description": "Configure SNMP communities and contacts.",
                "category": "Management",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "community": {"type": "string"},
                        "contact": {"type": "string"}
                    }
                }
            },
        )

        # ---------------------------
        # Task Implementations (Service Specific Config)
        # ---------------------------
        # Data Service - Cisco (Hardcoded VLAN 100 via implementation config)
        TaskImplementation.objects.get_or_create(
            task=service_data,
            manufacturer=cisco,
            platform=iosxe,
            name="Cisco IOS-XE: Data Service (VLAN 100)",
            defaults={
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "interface {{ intended.inputs.interface_name }}\n"
                    " description Data Service - Jack {{ intended.inputs.jack_name }}\n"
                    " switchport mode access\n"
                    " switchport access vlan 100\n"
                    " spanning-tree portfast\n"
                ),
                "provider_config": napalm_cfg,
            }
        )

        # Voice Service - Cisco (Hardcoded VLAN 200 via implementation config)
        TaskImplementation.objects.get_or_create(
            task=service_voice,
            manufacturer=cisco,
            platform=iosxe,
            name="Cisco IOS-XE: Voice Service (VLAN 200)",
            defaults={
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "interface {{ intended.inputs.interface_name }}\n"
                    " description Voice Service - Jack {{ intended.inputs.jack_name }}\n"
                    " switchport mode access\n"
                    " switchport access vlan 100\n"
                    " switchport voice vlan 200\n"
                    " spanning-tree portfast\n"
                ),
                "provider_config": napalm_cfg,
            }
        )

        # ---------------------------
        # Workflows
        # ---------------------------
        wf_vlan, _ = Workflow.objects.get_or_create(
            slug="standard-vlan-creation",
            defaults={
                "name": "Standard VLAN Creation",
                "description": "End-to-end VLAN creation with audit trail.",
                "category": "Self-Service",
                "enabled": True,
            }
        )
        WorkflowStep.objects.get_or_create(workflow=wf_vlan, order=10, defaults={"name": "Push Config", "step_type": WorkflowStep.StepTypeChoices.TASK, "task": task_vlan})

        wf_port, _ = Workflow.objects.get_or_create(
            slug="port-vlan-change",
            defaults={
                "name": "Port VLAN Change Request",
                "description": "Change the VLAN of a room jack port.",
                "category": "Self-Service",
                "enabled": True,
            }
        )
        # We'll use the same task_vlan for demo or create a new one if needed.
        # For this demo, let's reuse task_vlan but it would usually be a specialized task.
        WorkflowStep.objects.get_or_create(workflow=wf_port, order=10, defaults={"name": "Update Port", "step_type": WorkflowStep.StepTypeChoices.TASK, "task": task_vlan})

        # ---------------------------
        # Request Forms
        # ---------------------------
        rf_vlan, _ = RequestForm.objects.get_or_create(
            slug="vlan-request",
            defaults={
                "name": "Request New VLAN",
                "workflow": wf_vlan,
                "published": True,
                "category": "Layer 2",
            }
        )
        rf_vlan.fields.all().delete()

        rf_port, _ = RequestForm.objects.get_or_create(
            slug="port-vlan-change-request",
            defaults={
                "name": "VLAN Change Request (Jack-based)",
                "workflow": wf_port,
                "published": True,
                "category": "Self-Service",
            }
        )
        rf_port.fields.all().delete()
        
        ct_location = ContentType.objects.get(app_label="dcim", model="location")
        ct_device = ContentType.objects.get(app_label="dcim", model="device")
        
        ct_task = ContentType.objects.get(app_label="nautobot_network_provisioning", model="taskdefinition")
        
        RequestFormField.objects.create(
            form=rf_port,
            field_name="building",
            order=10,
            label="Building",
            required=True,
            lookup_type=RequestFormField.LookupTypeChoices.LOCATION_BY_TYPE,
            lookup_config={"type": "Building"},
            help_text="Select the building where the jack is located."
        )
        RequestFormField.objects.create(
            form=rf_port,
            field_name="room",
            order=20,
            label="Room",
            required=True,
            lookup_type=RequestFormField.LookupTypeChoices.LOCATION_BY_TYPE,
            lookup_config={"type": "Room", "parent_field": "building"},
            help_text="Select the room number."
        )
        RequestFormField.objects.create(
            form=rf_port,
            field_name="jack",
            order=30,
            label="Room Jack",
            required=True,
            lookup_type=RequestFormField.LookupTypeChoices.DEVICE_BY_ROLE,
            lookup_config={"role": "Demo", "location_field": "room"},
            queryset_filter={"device_type__model": "Wall Jack"},
            help_text="Select the physical wall jack identifier."
        )
        RequestFormField.objects.create(
            form=rf_port,
            field_name="service",
            order=40,
            label="Network Service",
            required=True,
            lookup_type=RequestFormField.LookupTypeChoices.TASK_BY_CATEGORY,
            lookup_config={"category": "Service Catalog"},
            help_text="Choose the type of service to provision on this jack."
        )
        RequestFormField.objects.create(
            form=rf_vlan,
            field_name="vlan_id",
            order=10,
            field_type=RequestFormField.FieldTypeChoices.NUMBER,
            label="VLAN ID",
            required=True,
        )
        RequestFormField.objects.create(
            form=rf_vlan,
            field_name="vlan_name",
            order=20,
            field_type=RequestFormField.FieldTypeChoices.TEXT,
            label="VLAN Name",
            required=False,
        )

        return (
            "Demo data populated successfully.\n"
            "- Manufacturers: Cisco, Arista\n"
            "- Platforms: IOS-XE, EOS\n"
            "- Tasks: Configure VLAN, Configure SNMP\n"
            "- Git Repo: Automation Catalog\n"
            "- Workflow: Standard VLAN Creation"
        )
