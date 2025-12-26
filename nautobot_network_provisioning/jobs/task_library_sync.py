"""
Task Library Sync v2.0

Bidirectional synchronization between YAML files in task-library/ and the database.

Supports:
- Import: YAML → Database (sync tasks from Git)
- Export: Database → YAML (export tasks for Git storage)

YAML files use the new v2 task format with:
- inputs: Low-code friendly variable definitions
- strategies: Platform-specific implementations with method types
"""
import os
import hashlib
import yaml
from datetime import datetime
from django.utils import timezone
from django.utils.text import slugify
from nautobot.apps.jobs import Job, register_jobs, BooleanVar, ChoiceVar
from nautobot.dcim.models import Platform
from nautobot_network_provisioning.models import (
    TaskIntent, 
    TaskStrategy,
    Workflow, 
    WorkflowStep,
    Folder
)


class SyncTaskLibrary(Job):
    """
    Synchronizes the Task Library between Git/Filesystem and Nautobot database.
    
    Supports bidirectional sync:
    - YAML → Database: Import tasks from task-library/ YAML files
    - Database → YAML: Export tasks to YAML files for version control
    """

    class Meta:
        name = "Sync Task Library (v2)"
        description = "Synchronize tasks between task-library/ YAML files and Nautobot database."
        has_sensitive_variables = False

    sync_direction = ChoiceVar(
        description="Sync direction",
        choices=[
            ("yaml_to_db", "Import: YAML → Database"),
            ("db_to_yaml", "Export: Database → YAML"),
        ],
        default="yaml_to_db"
    )
    
    dry_run = BooleanVar(
        description="Preview changes without applying",
        default=True
    )
    
    force_update = BooleanVar(
        description="Update even if content hash matches (force refresh)",
        default=False
    )

    def run(self, sync_direction, dry_run, force_update):
        self.dry_run = dry_run
        self.force_update = force_update
        self.stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        base_path = self._get_task_library_path()
        if not base_path:
            self.logger.error("task-library/ directory not found")
            return
        
        self.logger.info(f"Task library path: {base_path}")
        self.logger.info(f"Sync direction: {sync_direction}")
        self.logger.info(f"Dry run: {dry_run}")
        
        if sync_direction == "yaml_to_db":
            self._import_from_yaml(base_path)
        else:
            self._export_to_yaml(base_path)
        
        self.logger.info(f"Sync complete: {self.stats}")
    
    def _get_task_library_path(self):
        """Find the task-library directory."""
        # Try relative to current working directory
        if os.path.exists("task-library"):
            return os.path.abspath("task-library")
        
        # Try relative to Nautobot base
        possible_paths = [
            "/opt/nautobot/task-library",
            "/app/task-library",
            os.path.expanduser("~/nautobot/task-library"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # IMPORT: YAML → DATABASE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _import_from_yaml(self, base_path):
        """Import tasks from YAML files into the database."""
        self.logger.info("Importing tasks from YAML files...")
        
        for root, dirs, files in os.walk(base_path):
            # Skip workflow directory for task import
            if "workflows" in root or "_workflows" in root:
                continue
            
            for filename in files:
                if not filename.endswith((".yaml", ".yml")):
                    continue
                if filename.startswith("_"):
                    continue
                
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, base_path)
                
                try:
                    self._import_task_file(file_path, relative_path)
                except Exception as e:
                    self.logger.error(f"Error importing {relative_path}: {e}")
                    self.stats["errors"] += 1
        
        # Import workflows
        self._import_workflows(base_path)
    
    def _import_task_file(self, file_path, relative_path):
        """Import a single task YAML file."""
        with open(file_path, "r") as f:
            content = f.read()
            data = yaml.safe_load(content)
        
        if not data or not data.get("name"):
            self.logger.warning(f"Skipping {relative_path}: missing 'name' field")
            self.stats["skipped"] += 1
            return
        
        # Calculate content hash for change detection
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        
        # Check if task exists and is unchanged
        slug = data.get("slug") or slugify(data["name"]).replace("-", "_")
        existing = TaskIntent.objects.filter(slug=slug).first()
        
        if existing and existing.source_hash == content_hash and not self.force_update:
            self.logger.debug(f"Skipping {relative_path}: unchanged")
            self.stats["skipped"] += 1
            return
        
        # Parse inputs (v2 format) or fallback to legacy format
        inputs = data.get("inputs", [])
        if not inputs and data.get("variables"):
            # Convert legacy 'variables' to 'inputs'
            inputs = self._convert_legacy_variables(data.get("variables", []))
        
        # Infer category from directory structure
        category = data.get("category", "")
        if not category:
            parts = relative_path.split(os.sep)
            if len(parts) > 1:
                category = parts[0].replace("-", " ").title()
        
        self.logger.info(f"{'[DRY RUN] Would import' if self.dry_run else 'Importing'}: {data['name']}")
        
        if not self.dry_run:
            intent, created = TaskIntent.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": data["name"],
                    "description": data.get("description", ""),
                    "category": category,
                    "inputs": inputs,
                    "input_schema": data.get("input_schema"),  # Legacy
                    "variable_mappings": data.get("variables"),  # Legacy
                    "validation_config": data.get("validation"),
                    "rollback_template": data.get("rollback", {}).get("template", "") if isinstance(data.get("rollback"), dict) else "",
                    "source_file": relative_path,
                    "source_hash": content_hash,
                    "last_synced": timezone.now(),
                }
            )
            
            if created:
                self.stats["created"] += 1
            else:
                self.stats["updated"] += 1
            
            # Import strategies
            self._import_strategies(intent, data, relative_path)
        else:
            self.stats["updated" if existing else "created"] += 1
    
    def _import_strategies(self, intent, data, relative_path):
        """Import strategies (implementations) for a task."""
        strategies = data.get("strategies", [])
        
        # Legacy: single implementation in task file
        if not strategies and data.get("template_content") or data.get("template"):
            strategies = [{
                "name": f"{data.get('manufacturer', '')} {data.get('platform', 'Default')}".strip(),
                "platform": data.get("platform"),
                "method": self._infer_method(data.get("implementation_type", "jinja2_config")),
                "priority": data.get("priority", 100),
                "enabled": data.get("enabled", True),
                "template": data.get("template_content") or data.get("template", "")
            }]
        
        for strat_data in strategies:
            platform_identifier = strat_data.get("platform")
            if not platform_identifier:
                # Try to infer from directory structure
                parts = relative_path.split(os.sep)
                if len(parts) >= 2:
                    platform_identifier = parts[-2]  # e.g., "ios" from "cisco/ios/task.yaml"
            
            if not platform_identifier:
                self.logger.warning(f"No platform for strategy in {relative_path}")
                continue
            
            # Find platform by slug or name
            platform = Platform.objects.filter(slug=platform_identifier).first()
            if not platform:
                platform = Platform.objects.filter(name__icontains=platform_identifier).first()
            
            if not platform:
                self.logger.warning(f"Platform not found: {platform_identifier}")
                continue
            
            method = strat_data.get("method", "cli_config")
            template_content = strat_data.get("template") or strat_data.get("template_content", "")
            
            # Handle API config for rest_api method
            method_config = None
            if method == "rest_api" and strat_data.get("api_config"):
                method_config = strat_data["api_config"]
            
            TaskStrategy.objects.update_or_create(
                task_intent=intent,
                platform=platform,
                method=method,
                defaults={
                    "name": strat_data.get("name", f"{platform.name} {method}"),
                    "priority": strat_data.get("priority", 100),
                    "enabled": strat_data.get("enabled", True),
                    "template_content": template_content,
                    "method_config": method_config,
                }
            )
    
    def _import_workflows(self, base_path):
        """Import workflows from the _workflows or workflows directory."""
        for subdir in ["workflows", "_workflows"]:
            workflow_path = os.path.join(base_path, subdir)
            if not os.path.exists(workflow_path):
                continue
            
            for filename in os.listdir(workflow_path):
                if not filename.endswith((".yaml", ".yml")):
                    continue
                
                file_path = os.path.join(workflow_path, filename)
                relative_path = os.path.relpath(file_path, base_path)
                
                try:
                    with open(file_path, "r") as f:
                        data = yaml.safe_load(f)
                    
                    if not data or not data.get("name"):
                        continue
                    
                    self.logger.info(f"{'[DRY RUN] Would import' if self.dry_run else 'Importing'} workflow: {data['name']}")
                    
                    if not self.dry_run:
                        slug = data.get("slug") or slugify(data["name"])
                        workflow, _ = Workflow.objects.update_or_create(
                            slug=slug,
                            defaults={
                                "name": data["name"],
                                "description": data.get("description", ""),
                            }
                        )
                        
                        # Sync workflow steps
                        workflow.steps.all().delete()
                        for i, step_data in enumerate(data.get("steps", [])):
                            task_slug = step_data.get("task")
                            task = TaskIntent.objects.filter(slug=task_slug).first()
                            if task:
                                WorkflowStep.objects.create(
                                    workflow=workflow,
                                    task_intent=task,
                                    weight=(i + 1) * 10,
                                    parameters=step_data.get("parameters", {})
                                )
                
                except Exception as e:
                    self.logger.error(f"Error importing workflow {relative_path}: {e}")
    
    def _convert_legacy_variables(self, variables):
        """Convert legacy 'variables' format to new 'inputs' format."""
        inputs = []
        for var in variables:
            inputs.append({
                "name": var.get("name"),
                "label": var.get("description", var.get("name")),
                "type": "string",
                "required": var.get("required", True),
                "source": var.get("source", "input"),
                "source_path": var.get("path") or var.get("fallback"),
                "default": var.get("default"),
                "help": var.get("description", "")
            })
        return inputs
    
    def _infer_method(self, impl_type):
        """Infer method from legacy implementation_type."""
        mapping = {
            "jinja2_config": "cli_config",
            "jinja2": "cli_config",
            "python": "python",
            "api": "rest_api",
            "netconf": "netconf",
        }
        return mapping.get(impl_type, "cli_config")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXPORT: DATABASE → YAML
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _export_to_yaml(self, base_path):
        """Export tasks from database to YAML files."""
        self.logger.info("Exporting tasks to YAML files...")
        
        for intent in TaskIntent.objects.all():
            try:
                self._export_task(intent, base_path)
            except Exception as e:
                self.logger.error(f"Error exporting {intent.name}: {e}")
                self.stats["errors"] += 1
    
    def _export_task(self, intent, base_path):
        """Export a single task to YAML."""
        # Determine output path
        if intent.source_file:
            output_path = os.path.join(base_path, intent.source_file)
        else:
            # Create path based on category and slug
            category_dir = slugify(intent.category or "general")
            output_path = os.path.join(base_path, category_dir, f"{intent.slug}.yaml")
        
        # Build YAML structure
        data = {
            "name": intent.name,
            "slug": intent.slug,
            "description": intent.description,
            "category": intent.category,
            "inputs": intent.inputs or [],
        }
        
        # Add validation if present
        if intent.validation_config:
            data["validation"] = intent.validation_config
        
        # Add rollback if present
        if intent.rollback_template:
            data["rollback"] = {"template": intent.rollback_template}
        
        # Add strategies
        strategies = []
        for strat in intent.strategies.all():
            strat_data = {
                "name": strat.name,
                "platform": strat.platform.slug if strat.platform else None,
                "method": strat.method,
                "priority": strat.priority,
                "enabled": strat.enabled,
                "template": strat.template_content,
            }
            if strat.method_config:
                strat_data["method_config"] = strat.method_config
            strategies.append(strat_data)
        
        if strategies:
            data["strategies"] = strategies
        
        self.logger.info(f"{'[DRY RUN] Would export' if self.dry_run else 'Exporting'}: {intent.name} -> {output_path}")
        
        if not self.dry_run:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write YAML
            with open(output_path, "w") as f:
                f.write(f"# Task: {intent.name}\n")
                f.write(f"# Exported from Nautobot at {datetime.now().isoformat()}\n")
                f.write("---\n")
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            # Update source_file and hash
            content_hash = hashlib.sha256(open(output_path, "rb").read()).hexdigest()[:32]
            intent.source_file = os.path.relpath(output_path, base_path)
            intent.source_hash = content_hash
            intent.last_synced = timezone.now()
            intent.save()
        
        self.stats["updated"] += 1


# Legacy job name for backwards compatibility
class TaskLibrarySync(SyncTaskLibrary):
    """Legacy alias for SyncTaskLibrary."""
    
    class Meta:
        name = "Sync Task Library (Legacy)"
        description = "Legacy sync job - use 'Sync Task Library (v2)' instead."


register_jobs(SyncTaskLibrary, TaskLibrarySync)
