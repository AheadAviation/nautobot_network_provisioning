"""Phase 7: Git import/export jobs.

This provides a practical first cut at GitOps:
- Export TaskDefinitions, TaskImplementations, Workflows (+ steps) to YAML files in a Git repo working directory.
- Import those YAML files back into Nautobot (create/update).

It intentionally keeps the schema simple and human-reviewable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from nautobot.apps.jobs import Job

from nautobot_network_provisioning.models import (
    RequestForm,
    RequestFormField,
    TaskDefinition,
    TaskImplementation,
    Workflow,
    WorkflowStep
)


def _resolve_repo_path(repo: Any) -> Path:  # noqa: ANN401
    """Best-effort resolve a local filesystem path for a Nautobot GitRepository."""

    for attr in ("filesystem_path", "repo_path", "path", "local_path", "working_directory"):
        val = getattr(repo, attr, None)
        if callable(val):
            try:
                val = val()
            except Exception:  # noqa: BLE001
                val = None
        if val:
            return Path(str(val))
    raise ValueError("Unable to resolve local path for GitRepository; unsupported Nautobot version/field set.")


def _write_yaml(path: Path, data: Any) -> None:  # noqa: ANN401
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


def _read_yaml(path: Path) -> Any:  # noqa: ANN401
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ExportAutomationToGit(Job):
    """Export automation definitions to a Git working directory."""

    class Meta:  # noqa: D106
        name = "Export Automation to Git"
        description = "Export Tasks/Implementations/Workflows to YAML files in a Git repository working directory."

    def run(self, output_dir: str = "automation_definitions", repo_path: str = ""):  # noqa: D102
        base = Path(repo_path) if repo_path else None
        if base is None:
            raise ValueError("repo_path is required (path to a checked-out Git working directory).")
        base = base.expanduser().resolve()

        out = base / output_dir
        out.mkdir(parents=True, exist_ok=True)

        tasks = []
        for t in TaskDefinition.objects.all().order_by("name"):
            tasks.append(
                {
                    "name": t.name,
                    "slug": t.slug,
                    "description": t.description,
                    "category": t.category,
                    "input_schema": t.input_schema,
                    "output_schema": t.output_schema,
                    "documentation": t.documentation,
                    "enabled": True,
                }
            )
        _write_yaml(out / "tasks.yaml", {"tasks": tasks})

        impls = []
        for i in TaskImplementation.objects.select_related("task", "manufacturer", "platform", "provider_config").prefetch_related(
            "software_versions"
        ):
            impls.append(
                {
                    "task": i.task.slug,
                    "name": i.name,
                    "manufacturer": i.manufacturer.name,
                    "platform": getattr(i.platform, "slug", None),
                    "software_versions": [sv.version for sv in i.software_versions.all()],
                    "priority": i.priority,
                    "implementation_type": i.implementation_type,
                    "template_content": i.template_content,
                    "action_config": i.action_config,
                    "pre_checks": i.pre_checks,
                    "post_checks": i.post_checks,
                    "provider_config": getattr(i.provider_config, "name", None),
                    "enabled": i.enabled,
                }
            )
        _write_yaml(out / "task_implementations.yaml", {"task_implementations": impls})

        workflows = []
        for w in Workflow.objects.all().order_by("name"):
            steps = []
            for s in WorkflowStep.objects.filter(workflow=w).select_related("task").order_by("order", "name"):
                steps.append(
                    {
                        "order": s.order,
                        "name": s.name,
                        "step_type": s.step_type,
                        "task": getattr(s.task, "slug", None),
                        "input_mapping": s.input_mapping,
                        "output_mapping": s.output_mapping,
                        "condition": s.condition,
                        "on_failure": s.on_failure,
                        "config": s.config,
                    }
                )
            workflows.append(
                {
                    "name": w.name,
                    "slug": w.slug,
                    "description": w.description,
                    "category": w.category,
                    "version": w.version,
                    "enabled": w.enabled,
                    "approval_required": w.approval_required,
                    "schedule_allowed": w.schedule_allowed,
                    "input_schema": w.input_schema,
                    "default_inputs": w.default_inputs,
                    "steps": steps,
                }
            )
        _write_yaml(out / "workflows.yaml", {"workflows": workflows})

        request_forms = []
        for rf in RequestForm.objects.all().select_related("workflow").order_by("name"):
            fields = []
            for f in RequestFormField.objects.filter(form=rf).select_related("object_type", "depends_on").order_by("order"):
                fields.append({
                    "order": f.order,
                    "field_name": f.field_name,
                    "field_type": f.field_type,
                    "label": f.label,
                    "help_text": f.help_text,
                    "required": f.required,
                    "default_value": f.default_value,
                    "validation_rules": f.validation_rules,
                    "choices": f.choices,
                    "lookup_type": f.lookup_type,
                    "lookup_config": f.lookup_config,
                    "object_type": f"{f.object_type.app_label}.{f.object_type.model}" if f.object_type else None,
                    "queryset_filter": f.queryset_filter,
                    "depends_on": f.depends_on.field_name if f.depends_on else None,
                    "show_condition": f.show_condition,
                    "map_to": f.map_to,
                })
            request_forms.append({
                "name": rf.name,
                "slug": rf.slug,
                "description": rf.description,
                "category": rf.category,
                "icon": rf.icon,
                "workflow": rf.workflow.slug,
                "published": rf.published,
                "fields": fields,
            })
        _write_yaml(out / "request_forms.yaml", {"request_forms": request_forms})

        return f"Exported to {out}"


class ImportAutomationFromGit(Job):
    """Import automation definitions from YAML files."""

    class Meta:  # noqa: D106
        name = "Import Automation from Git"
        description = "Import Tasks/Implementations/Workflows from YAML files in a working directory."

    def run(self, input_dir: str = "automation_definitions", repo_path: str = "", update_existing: bool = True):  # noqa: D102
        base = Path(repo_path) if repo_path else None
        if base is None:
            raise ValueError("repo_path is required (path to a checked-out Git working directory).")
        base = base.expanduser().resolve()
        inp = base / input_dir
        if not inp.exists():
            raise ValueError(f"Input directory not found: {inp}")

        from nautobot.dcim.models import Manufacturer, Platform, SoftwareVersion
        from django.contrib.contenttypes.models import ContentType

        created = {"tasks": 0, "implementations": 0, "workflows": 0, "steps": 0, "request_forms": 0, "fields": 0}

        tasks_data = _read_yaml(inp / "tasks.yaml").get("tasks", [])
        for t in tasks_data:
            obj, was_created = TaskDefinition.objects.get_or_create(slug=t["slug"], defaults={"name": t["name"]})
            if update_existing or was_created:
                obj.name = t.get("name", obj.name)
                obj.description = t.get("description", obj.description or "")
                obj.category = t.get("category", obj.category or "")
                obj.input_schema = t.get("input_schema", obj.input_schema or {})
                obj.output_schema = t.get("output_schema", obj.output_schema or {})
                obj.documentation = t.get("documentation", obj.documentation or "")
                obj.save()
            if was_created:
                created["tasks"] += 1

        impls_data = _read_yaml(inp / "task_implementations.yaml").get("task_implementations", [])
        for i in impls_data:
            task = TaskDefinition.objects.get(slug=i["task"])
            manufacturer, _ = Manufacturer.objects.get_or_create(name=i["manufacturer"], defaults={"slug": i["manufacturer"].lower().replace(" ", "-")})
            platform = None
            if i.get("platform"):
                platform = Platform.objects.filter(slug=i["platform"]).first()
            obj, was_created = TaskImplementation.objects.get_or_create(
                task=task,
                manufacturer=manufacturer,
                platform=platform,
                name=i["name"],
                defaults={"implementation_type": i.get("implementation_type", TaskImplementation.ImplementationTypeChoices.JINJA2_CONFIG)},
            )
            if update_existing or was_created:
                obj.priority = int(i.get("priority", obj.priority))
                obj.implementation_type = i.get("implementation_type", obj.implementation_type)
                obj.template_content = i.get("template_content", obj.template_content or "")
                obj.action_config = i.get("action_config", obj.action_config or {})
                obj.pre_checks = i.get("pre_checks", obj.pre_checks or [])
                obj.post_checks = i.get("post_checks", obj.post_checks or [])
                obj.enabled = bool(i.get("enabled", obj.enabled))
                obj.save()

                versions = i.get("software_versions") or []
                if versions:
                    sv_qs = SoftwareVersion.objects.filter(version__in=versions)
                    obj.software_versions.set(sv_qs)
            if was_created:
                created["implementations"] += 1

        workflows_data = _read_yaml(inp / "workflows.yaml").get("workflows", [])
        for w in workflows_data:
            obj, was_created = Workflow.objects.get_or_create(slug=w["slug"], defaults={"name": w["name"]})
            if update_existing or was_created:
                obj.name = w.get("name", obj.name)
                obj.description = w.get("description", obj.description or "")
                obj.category = w.get("category", obj.category or "")
                obj.version = w.get("version", obj.version or "")
                obj.enabled = bool(w.get("enabled", obj.enabled))
                obj.approval_required = bool(w.get("approval_required", obj.approval_required))
                obj.schedule_allowed = bool(w.get("schedule_allowed", obj.schedule_allowed))
                obj.input_schema = w.get("input_schema", obj.input_schema or {})
                obj.default_inputs = w.get("default_inputs", obj.default_inputs or {})
                obj.save()
            if was_created:
                created["workflows"] += 1

            # Replace steps if update_existing; else only add missing ones.
            if update_existing:
                WorkflowStep.objects.filter(workflow=obj).delete()

            for s in w.get("steps", []):
                task = None
                if s.get("task"):
                    task = TaskDefinition.objects.filter(slug=s["task"]).first()
                WorkflowStep.objects.create(
                    workflow=obj,
                    order=int(s.get("order", 0)),
                    name=s.get("name", "Step"),
                    step_type=s.get("step_type", WorkflowStep.StepTypeChoices.TASK),
                    task=task,
                    input_mapping=s.get("input_mapping", {}),
                    output_mapping=s.get("output_mapping", {}),
                    condition=s.get("condition", ""),
                    on_failure=s.get("on_failure", WorkflowStep.OnFailureChoices.STOP),
                    config=s.get("config", {}),
                )
                created["steps"] += 1

        request_forms_data = _read_yaml(inp / "request_forms.yaml").get("request_forms", [])
        for rf in request_forms_data:
            workflow = Workflow.objects.get(slug=rf["workflow"])
            obj, was_created = RequestForm.objects.get_or_create(slug=rf["slug"], defaults={"name": rf["name"], "workflow": workflow})
            if update_existing or was_created:
                obj.name = rf.get("name", obj.name)
                obj.description = rf.get("description", obj.description or "")
                obj.category = rf.get("category", obj.category or "")
                obj.icon = rf.get("icon", obj.icon or "")
                obj.workflow = workflow
                obj.published = bool(rf.get("published", obj.published))
                obj.save()
            if was_created:
                created["request_forms"] += 1
            
            if update_existing:
                RequestFormField.objects.filter(form=obj).delete()
            
            for f in rf.get("fields", []):
                object_type = None
                if f.get("object_type"):
                    app_label, model = f["object_type"].split(".")
                    object_type = ContentType.objects.get(app_label=app_label, model=model)
                
                depends_on = None
                if f.get("depends_on"):
                    depends_on = RequestFormField.objects.filter(form=obj, field_name=f["depends_on"]).first()
                
                RequestFormField.objects.create(
                    form=obj,
                    order=int(f.get("order", 0)),
                    field_name=f["field_name"],
                    field_type=f.get("field_type", RequestFormField.FieldTypeChoices.TEXT),
                    label=f.get("label", f["field_name"]),
                    help_text=f.get("help_text", ""),
                    required=bool(f.get("required", False)),
                    default_value=f.get("default_value", {}),
                    validation_rules=f.get("validation_rules", {}),
                    choices=f.get("choices", []),
                    lookup_type=f.get("lookup_type", RequestFormField.LookupTypeChoices.MANUAL),
                    lookup_config=f.get("lookup_config", {}),
                    object_type=object_type,
                    queryset_filter=f.get("queryset_filter", {}),
                    depends_on=depends_on,
                    show_condition=f.get("show_condition", ""),
                    map_to=f.get("map_to", ""),
                )
                created["fields"] += 1

        return f"Imported. Created: {created}"


