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
        from nautobot.dcim.models import Device, DeviceType, Manufacturer, Platform
        from nautobot.dcim.models import Location, LocationType
        from nautobot.extras.models import Role, Status, GitRepository
        from nautobot.extras.choices import GitRepositoryContentTypeChoices

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

        loc_type, _ = LocationType.objects.get_or_create(name="Site", defaults={"nestable": True})
        demo_loc, _ = Location.objects.get_or_create(
            name="Demo HQ",
            defaults={"location_type": loc_type, "status": status_active},
        )
        
        # Manufacturers & Platforms
        cisco, _ = Manufacturer.objects.get_or_create(name="Cisco", defaults={"slug": "cisco"})
        arista, _ = Manufacturer.objects.get_or_create(name="Arista", defaults={"slug": "arista"})
        
        iosxe, _ = Platform.objects.get_or_create(name="Cisco IOS-XE", defaults={"manufacturer": cisco, "slug": "cisco-ios-xe", "napalm_driver": "ios"})
        eos, _ = Platform.objects.get_or_create(name="Arista EOS", defaults={"manufacturer": arista, "slug": "arista-eos", "napalm_driver": "eos"})

        # Demo Devices
        dt_cisco, _ = DeviceType.objects.get_or_create(
            manufacturer=cisco,
            model="C9300-48P",
            defaults={"slug": "c9300-48p", "u_height": 1}
        )
        dt_arista, _ = DeviceType.objects.get_or_create(
            manufacturer=arista,
            model="DCS-7050SX",
            defaults={"slug": "dcs-7050sx", "u_height": 1}
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
        # Task Definitions
        # ---------------------------
        task_vlan, _ = TaskDefinition.objects.get_or_create(
            slug="configure-vlan",
            defaults={
                "name": "Configure VLAN",
                "description": "Create or update a VLAN on the device.",
                "category": "Layer 2",
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
        # Task Implementations
        # ---------------------------
        # VLAN - Cisco
        TaskImplementation.objects.get_or_create(
            task=task_vlan,
            manufacturer=cisco,
            platform=iosxe,
            name="Cisco IOS-XE: VLAN",
            defaults={
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "vlan {{ intended.inputs.vlan_id }}\n"
                    " name {{ intended.inputs.vlan_name | default('VLAN_' ~ intended.inputs.vlan_id) }}\n"
                ),
                "provider_config": napalm_cfg,
            }
        )
        # VLAN - Arista
        TaskImplementation.objects.get_or_create(
            task=task_vlan,
            manufacturer=arista,
            platform=eos,
            name="Arista EOS: VLAN",
            defaults={
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "vlan {{ intended.inputs.vlan_id }}\n"
                    "   name {{ intended.inputs.vlan_name | default('VLAN_' ~ intended.inputs.vlan_id) }}\n"
                ),
                "provider_config": napalm_cfg,
            }
        )
        # SNMP - Cisco
        TaskImplementation.objects.get_or_create(
            task=task_snmp,
            manufacturer=cisco,
            platform=iosxe,
            name="Cisco IOS-XE: SNMP",
            defaults={
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "snmp-server community {{ intended.inputs.community | default('public') }} RO\n"
                    "snmp-server contact {{ intended.inputs.contact | default('NetOps') }}\n"
                ),
                "provider_config": napalm_cfg,
            }
        )
        # SNMP - Arista
        TaskImplementation.objects.get_or_create(
            task=task_snmp,
            manufacturer=arista,
            platform=eos,
            name="Arista EOS: SNMP",
            defaults={
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "snmp-server community {{ intended.inputs.community | default('public') }} ro\n"
                    "snmp-server contact {{ intended.inputs.contact | default('NetOps') }}\n"
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
        RequestFormField.objects.get_or_create(
            form=rf_vlan,
            field_name="vlan_id",
            defaults={
                "order": 10,
                "field_type": RequestFormField.FieldTypeChoices.NUMBER,
                "label": "VLAN ID",
                "required": True,
            }
        )
        RequestFormField.objects.get_or_create(
            form=rf_vlan,
            field_name="vlan_name",
            defaults={
                "order": 20,
                "field_type": RequestFormField.FieldTypeChoices.TEXT,
                "label": "VLAN Name",
                "required": False,
            }
        )

        return (
            "Demo data populated successfully.\n"
            "- Manufacturers: Cisco, Arista\n"
            "- Platforms: IOS-XE, EOS\n"
            "- Tasks: Configure VLAN, Configure SNMP\n"
            "- Git Repo: Automation Catalog\n"
            "- Workflow: Standard VLAN Creation"
        )


