"""Demo data loader job.

Provides a checkbox-based interface to load specific categories of demo data:
- Core Nautobot: Locations, Racks, Circuits, Devices
- App-specific: Providers, Tasks, Workflows, Request Forms
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from nautobot.apps.jobs import BooleanVar, Job

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


class DemoDataLoader(Job):
    """Load demo data with granular control over categories."""

    load_locations = BooleanVar(default=True, description="Load Locations (Regions, Sites)")
    load_racks = BooleanVar(default=True, description="Load Racks")
    load_circuits = BooleanVar(default=True, description="Load Circuit Types, Providers, and Circuits")
    load_devices = BooleanVar(default=True, description="Load Manufacturers, Platforms, Device Types, and Devices")
    load_app_logic = BooleanVar(default=True, description="Load App-specific Providers, Tasks, Workflows, and Request Forms")

    class Meta:
        name = "Demo Data Loader"
        description = "Selectively load core Nautobot data and app-specific automation content."

    def _get_or_create_named_with_optional_slug(self, model, name: str, slug: str):
        """Get/create a model that may or may not have a `slug` field (varies by Nautobot version)."""
        try:
            model._meta.get_field("slug")
            obj, _ = model.objects.get_or_create(name=name, defaults={"slug": slug})
            return obj
        except Exception:
            obj, _ = model.objects.get_or_create(name=name)
            return obj

    def _filter_defaults_for_model(self, model, defaults: dict):
        """Remove keys from defaults that don't exist as concrete model fields."""
        field_names = {f.name for f in model._meta.fields}
        return {k: v for k, v in (defaults or {}).items() if k in field_names}

    def _get_status(self, name, content_type=None):
        from nautobot.extras.models import Status
        status = Status.objects.filter(name=name).first()
        if not status:
            status = self._get_or_create_named_with_optional_slug(Status, name=name, slug=name.lower())
        if content_type and not status.content_types.filter(pk=content_type.pk).exists():
            status.content_types.add(content_type)
        return status

    def run(self, load_locations, load_racks, load_circuits, load_devices, load_app_logic):
        results = []

        # 1. Locations
        if load_locations:
            self.logger.info("Loading locations...")
            loc_results = self._load_locations()
            results.append(loc_results)

        # 2. Racks
        if load_racks:
            self.logger.info("Loading racks...")
            rack_results = self._load_racks()
            results.append(rack_results)

        # 3. Circuits
        if load_circuits:
            self.logger.info("Loading circuits...")
            circuit_results = self._load_circuits()
            results.append(circuit_results)

        # 4. Devices
        if load_devices:
            self.logger.info("Loading devices...")
            device_results = self._load_devices()
            results.append(device_results)

        # 5. App Logic
        if load_app_logic:
            self.logger.info("Loading app-specific logic...")
            app_results = self._load_app_logic()
            results.append(app_results)

        return "\n".join(results)

    def _load_locations(self):
        from nautobot.dcim.models import Location, LocationType
        
        ct_location = ContentType.objects.get_for_model(Location)
        status_active = self._get_status("Active", ct_location)
        
        # Site Type
        site_type, _ = LocationType.objects.get_or_create(
            name="Site",
            defaults={"nestable": True}
        )
        if not site_type.content_types.filter(pk=ct_location.pk).exists():
            site_type.content_types.add(ct_location)
        
        # Locations
        loc1, _ = Location.objects.get_or_create(
            name="Demo Datacenter 1",
            defaults={"location_type": site_type, "status": status_active}
        )
        loc2, _ = Location.objects.get_or_create(
            name="Demo Branch 1",
            defaults={"location_type": site_type, "status": status_active}
        )
        
        return f"Created/updated 2 locations (Site type: {site_type.name})"

    def _load_racks(self):
        from nautobot.dcim.models import Location, Rack, RackGroup
        
        ct_rack = ContentType.objects.get_for_model(Rack)
        status_active = self._get_status("Active", ct_rack)
        loc = Location.objects.filter(name="Demo Datacenter 1").first()
        if not loc:
            return "Skipped racks: Demo Datacenter 1 not found."

        rg, _ = RackGroup.objects.get_or_create(
            name="Demo Racks",
            location=loc
        )
        
        r1, _ = Rack.objects.get_or_create(
            name="Rack-01",
            location=loc,
            defaults={"rack_group": rg, "status": status_active, "u_height": 42}
        )
        
        return f"Created/updated 1 rack group and 1 rack in {loc.name}"

    def _load_circuits(self):
        from nautobot.circuits.models import Circuit, CircuitType, Provider as CircuitProvider
        
        ct_circuit = ContentType.objects.get_for_model(Circuit)
        status_active = self._get_status("Active", ct_circuit)
        
        ctype, _ = CircuitType.objects.get_or_create(name="Internet", defaults=self._filter_defaults_for_model(CircuitType, {"slug": "internet"}))
        cprov, _ = CircuitProvider.objects.get_or_create(name="Demo Telecom", defaults=self._filter_defaults_for_model(CircuitProvider, {"slug": "demo-telecom"}))
        
        c1, _ = Circuit.objects.get_or_create(
            cid="DEMO-001",
            defaults={
                "provider": cprov,
                "circuit_type": ctype,
                "status": status_active,
            }
        )
        
        return "Created/updated circuit type, provider, and 1 circuit (DEMO-001)"

    def _load_devices(self):
        from nautobot.dcim.models import Device, DeviceType, Manufacturer, Platform, Location
        from nautobot.extras.models import Role
        
        ct_device = ContentType.objects.get_for_model(Device)
        status_active = self._get_status("Active", ct_device)
        loc = Location.objects.filter(name="Demo Datacenter 1").first()
        if not loc:
            return "Skipped devices: Demo Datacenter 1 not found."

        role_demo = Role.objects.filter(name="Demo").first()
        if not role_demo:
            role_demo = self._get_or_create_named_with_optional_slug(Role, name="Demo", slug="demo")
        if not role_demo.content_types.filter(pk=ct_device.pk).exists():
            role_demo.content_types.add(ct_device)

        mfr, _ = Manufacturer.objects.get_or_create(name="DemoVendor", defaults=self._filter_defaults_for_model(Manufacturer, {"slug": "demo-vendor"}))
        platform, _ = Platform.objects.get_or_create(name="DemoOS", defaults=self._filter_defaults_for_model(Platform, {"slug": "demoos", "manufacturer": mfr}))
        
        dt, _ = DeviceType.objects.get_or_create(
            manufacturer=mfr,
            model="DemoSwitch-24T",
            defaults=self._filter_defaults_for_model(DeviceType, {"slug": "demoswitch-24t", "u_height": 1})
        )
        
        d1, _ = Device.objects.get_or_create(
            name="demo-sw-01",
            defaults={
                "device_type": dt,
                "location": loc,
                "status": status_active,
                "platform": platform,
                "role": role_demo,
            }
        )
        
        return f"Created/updated manufacturer, platform, device type, and 1 device ({d1.name})"

    def _load_app_logic(self):
        from nautobot.dcim.models import Manufacturer, Platform, Location
        
        mfr = Manufacturer.objects.filter(name="DemoVendor").first()
        platform = Platform.objects.filter(name="DemoOS").first()
        loc = Location.objects.filter(name="Demo Datacenter 1").first()

        # 1. Provider
        napalm_provider, _ = Provider.objects.get_or_create(
            name="napalm_cli",
            defaults={
                "driver_class": "nautobot_network_provisioning.services.providers.napalm_cli.NapalmCLIProvider",
                "description": "Demo NAPALM provider.",
                "capabilities": ["render", "diff", "apply"],
                "enabled": True,
            },
        )
        if platform:
            napalm_provider.supported_platforms.add(platform)

        napalm_cfg, _ = ProviderConfig.objects.get_or_create(
            provider=napalm_provider,
            name="demo-napalm",
            defaults={"enabled": True},
        )
        if loc:
            napalm_cfg.scope_locations.add(loc)

        # 2. Task
        task_vlan, _ = TaskDefinition.objects.get_or_create(
            slug="change-interface-vlan",
            defaults={
                "name": "Change Interface VLAN",
                "description": "Change the access VLAN on an interface.",
                "category": "Configuration",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "interface": {"type": "string"},
                        "vlan_id": {"type": "integer"}
                    },
                    "required": ["interface", "vlan_id"]
                },
            },
        )

        # 3. Implementation
        impl_vlan, _ = TaskImplementation.objects.get_or_create(
            task=task_vlan,
            manufacturer=mfr,
            platform=platform,
            name="DemoOS: change interface VLAN",
            defaults={
                "implementation_type": TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG,
                "template_content": (
                    "interface {{ intended.inputs.interface }}\n"
                    " switchport access vlan {{ intended.inputs.vlan_id }}\n"
                ),
                "provider_config": napalm_cfg,
                "enabled": True,
            },
        )

        # 4. Workflow
        wf, _ = Workflow.objects.get_or_create(
            slug="demo-change-vlan",
            defaults={
                "name": "Demo: Change VLAN",
                "description": "Demo workflow for changing a VLAN.",
                "category": "Day-2 Ops",
                "enabled": True,
                "approval_required": True,
            },
        )

        WorkflowStep.objects.get_or_create(
            workflow=wf,
            order=10,
            defaults={"name": "Render change", "step_type": WorkflowStep.StepTypeChoices.TASK, "task": task_vlan},
        )
        WorkflowStep.objects.get_or_create(
            workflow=wf,
            order=20,
            defaults={"name": "Approval", "step_type": WorkflowStep.StepTypeChoices.APPROVAL},
        )

        # 5. Request Form
        rf, rf_created = RequestForm.objects.get_or_create(
            slug="demo-change-vlan",
            defaults={
                "name": "Demo: Change Interface VLAN",
                "workflow": wf,
                "published": True,
            },
        )
        if not rf_created:
            rf.workflow = wf
            rf.published = True
            rf.save()

        RequestFormField.objects.get_or_create(
            form=rf,
            field_name="interface",
            defaults={
                "order": 10,
                "field_type": RequestFormField.FieldTypeChoices.TEXT,
                "label": "Interface",
                "required": True,
                "map_to": "intended.port.interface",
            },
        )
        RequestFormField.objects.get_or_create(
            form=rf,
            field_name="vlan_id",
            defaults={
                "order": 20,
                "field_type": RequestFormField.FieldTypeChoices.NUMBER,
                "label": "VLAN ID",
                "required": True,
                "map_to": "intended.port.untagged_vlan",
            },
        )

        # 6. A demo Execution
        Execution.objects.get_or_create(
            workflow=wf,
            status=Execution.StatusChoices.PENDING,
            defaults={
                "inputs": {"interface": "Ethernet1", "vlan_id": 123},
                "context": {"operation": "render"},
            },
        )

        return "Created/updated app-specific providers, tasks, workflows, and request forms."
