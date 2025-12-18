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
        from nautobot.extras.models import Role, Status

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
        if demo_loc.location_type_id != loc_type.id or demo_loc.status_id != status_active.id:
            demo_loc.location_type = loc_type
            demo_loc.status = status_active
            demo_loc.save()

        demo_mfr, _ = Manufacturer.objects.get_or_create(
            name="DemoVendor",
            defaults=_filter_defaults_for_model(Manufacturer, {"slug": "demo-vendor"}),
        )
        demo_platform, _ = Platform.objects.get_or_create(
            name="DemoOS",
            defaults=_filter_defaults_for_model(Platform, {"slug": "demoos"}),
        )

        demo_dt, _ = DeviceType.objects.get_or_create(
            manufacturer=demo_mfr,
            model="DemoSwitch-1U",
            defaults=_filter_defaults_for_model(DeviceType, {"slug": "demoswitch-1u", "u_height": 1, "is_full_depth": True}),
        )

        demo_device, _ = Device.objects.get_or_create(
            name="demo-switch-01",
            defaults={
                "device_type": demo_dt,
                "status": status_active,
                "role": role_demo,
                "location": demo_loc,
                "platform": demo_platform,
            },
        )
        # Ensure required FKs are present if the device already existed.
        changed = False
        for field, value in (
            ("device_type", demo_dt),
            ("status", status_active),
            ("role", role_demo),
            ("location", demo_loc),
            ("platform", demo_platform),
        ):
            if getattr(demo_device, f"{field}_id", None) != getattr(value, "id", None):
                setattr(demo_device, field, value)
                changed = True
        if changed:
            demo_device.save()

        # ---------------------------
        # Providers (our app models)
        # ---------------------------
        napalm_provider, _ = Provider.objects.get_or_create(
            name="napalm_cli",
            defaults={
                "driver_class": "nautobot_network_provisioning.services.providers.napalm_cli.NapalmCLIProvider",
                "description": "Demo NAPALM provider (prefers Nautobot-native Device.get_napalm_device()).",
                "capabilities": ["render", "diff", "apply"],
                "enabled": True,
            },
        )
        if demo_platform and not napalm_provider.supported_platforms.filter(pk=demo_platform.pk).exists():
            napalm_provider.supported_platforms.add(demo_platform)

        napalm_cfg, _ = ProviderConfig.objects.get_or_create(
            provider=napalm_provider,
            name="demo-napalm",
            defaults={"enabled": True, "settings": {}},
        )
        if not napalm_cfg.scope_locations.filter(pk=demo_loc.pk).exists():
            napalm_cfg.scope_locations.add(demo_loc)

        # ---------------------------
        # Tasks + Implementations
        # ---------------------------
        task_vlan, _ = TaskDefinition.objects.get_or_create(
            slug="change-interface-vlan",
            defaults={
                "name": "Change Interface VLAN",
                "description": "Change the access VLAN on an interface.",
                "category": "Configuration",
                "input_schema": {"type": "object", "properties": {"interface": {"type": "string"}, "vlan_id": {"type": "integer"}}},
                "output_schema": {"type": "object"},
                "documentation": "Demo task for changing an interface VLAN.",
            },
        )

        # A minimal template that will render even without a live interface object.
        impl_vlan, _ = TaskImplementation.objects.get_or_create(
            task=task_vlan,
            manufacturer=demo_mfr,
            platform=demo_platform,
            name="DemoOS: change interface VLAN",
            defaults={
                "priority": 100,
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "! Demo change VLAN\\n"
                    "interface {{ intended.inputs.interface | default('Ethernet1') }}\\n"
                    " switchport access vlan {{ intended.inputs.vlan_id | default(123) }}\\n"
                    " description {{ intended.inputs.description | default('Demo change') }}\\n"
                ),
                "provider_config": napalm_cfg,
                "enabled": True,
            },
        )
        # Keep provider_config linked if record already existed.
        if impl_vlan.provider_config_id != napalm_cfg.id:
            impl_vlan.provider_config = napalm_cfg
            impl_vlan.save()

        # ---------------------------
        # Workflow + Steps
        # ---------------------------
        wf, _ = Workflow.objects.get_or_create(
            slug="demo-change-vlan",
            defaults={
                "name": "Demo: Change VLAN (with approval)",
                "description": "Demo workflow showing a task + approval gate.",
                "category": "Day-2 Ops",
                "enabled": True,
                "approval_required": True,
                "schedule_allowed": False,
                "input_schema": {"type": "object"},
                "default_inputs": {},
            },
        )

        # Ensure steps exist (idempotent by order).
        step1, _ = WorkflowStep.objects.get_or_create(
            workflow=wf,
            order=10,
            defaults={"name": "Render change", "step_type": WorkflowStep.StepTypeChoices.TASK, "task": task_vlan},
        )
        if step1.task_id != task_vlan.id or step1.step_type != WorkflowStep.StepTypeChoices.TASK:
            step1.task = task_vlan
            step1.step_type = WorkflowStep.StepTypeChoices.TASK
            step1.save()

        approval, _ = WorkflowStep.objects.get_or_create(
            workflow=wf,
            order=20,
            defaults={"name": "Approval", "step_type": WorkflowStep.StepTypeChoices.APPROVAL},
        )
        if approval.step_type != WorkflowStep.StepTypeChoices.APPROVAL:
            approval.step_type = WorkflowStep.StepTypeChoices.APPROVAL
            approval.task = None
            approval.save()

        # ---------------------------
        # Request Form + Fields
        # ---------------------------
        rf, _ = RequestForm.objects.get_or_create(
            slug="demo-change-vlan",
            defaults={
                "name": "Demo: Change Interface VLAN",
                "description": "Example portal form demonstrating mapping + conditional field visibility.",
                "category": "Day-2 Ops",
                "icon": "mdi-swap-vertical",
                "workflow": wf,
                "published": True,
            },
        )
        if rf.workflow_id != wf.id or not rf.published:
            rf.workflow = wf
            rf.published = True
            rf.save()

        ct_device_model = ContentType.objects.get(app_label="dcim", model="device")

        # Define fields by name; update/create.
        field_specs = [
            dict(
                order=10,
                field_name="device",
                field_type=RequestFormField.FieldTypeChoices.OBJECT_SELECTOR,
                label="Device",
                help_text="Optional: pick a target device (demo includes demo-switch-01).",
                required=False,
                object_type=ct_device_model,
                validation_rules={"multi": False},
                map_to="target.device",
            ),
            dict(
                order=20,
                field_name="interface",
                field_type=RequestFormField.FieldTypeChoices.TEXT,
                label="Interface",
                help_text="Interface name, e.g. Ethernet1",
                required=True,
                map_to="intended.port.interface",
            ),
            dict(
                order=30,
                field_name="vlan_id",
                field_type=RequestFormField.FieldTypeChoices.NUMBER,
                label="New VLAN ID",
                help_text="Access VLAN number",
                required=True,
                map_to="intended.port.untagged_vlan",
            ),
            dict(
                order=40,
                field_name="advanced",
                field_type=RequestFormField.FieldTypeChoices.BOOLEAN,
                label="Advanced options",
                help_text="Show advanced options",
                required=False,
                map_to="meta.advanced",
            ),
            dict(
                order=50,
                field_name="description",
                field_type=RequestFormField.FieldTypeChoices.TEXT,
                label="Interface description",
                help_text="Only shown when Advanced options is enabled.",
                required=False,
                depends_on="advanced",  # wired below
                show_condition="input.advanced",
                map_to="intended.port.description",
            ),
        ]

        # Create/update fields; wire depends_on FK afterwards.
        by_name: dict[str, RequestFormField] = {}
        for spec in field_specs:
            fn = spec["field_name"]
            defaults = {
                "order": spec["order"],
                "field_type": spec["field_type"],
                "label": spec["label"],
                "help_text": spec.get("help_text", ""),
                "required": spec.get("required", False),
                "validation_rules": spec.get("validation_rules", {}),
                "choices": spec.get("choices", []),
                "object_type": spec.get("object_type", None),
                "queryset_filter": spec.get("queryset_filter", {}),
                "show_condition": spec.get("show_condition", ""),
                "map_to": spec.get("map_to", ""),
            }
            obj, _ = RequestFormField.objects.get_or_create(form=rf, field_name=fn, defaults=defaults)
            # Keep it updated.
            changed = False
            for k, v in defaults.items():
                if getattr(obj, k) != v:
                    setattr(obj, k, v)
                    changed = True
            if changed:
                obj.save()
            by_name[fn] = obj

        # depends_on
        desc = by_name.get("description")
        adv = by_name.get("advanced")
        if desc and adv and desc.depends_on_id != adv.id:
            desc.depends_on = adv
            desc.save(update_fields=["depends_on", "last_updated"])

        # ---------------------------
        # A demo Execution (for list view)
        # ---------------------------
        Execution.objects.get_or_create(
            workflow=wf,
            status=Execution.StatusChoices.PENDING,
            defaults={
                "inputs": {"interface": "Ethernet1", "vlan_id": 123, "description": "Demo port"},
                "context": {"operation": "render"},
            },
        )

        return (
            "Demo data created/updated:\n"
            "- ProviderConfig: demo-napalm\n"
            "- Device: demo-switch-01\n"
            "- Task: change-interface-vlan\n"
            "- Workflow: demo-change-vlan\n"
            "- Request Form: demo-change-vlan (published)\n"
            "- Execution: pending"
        )


