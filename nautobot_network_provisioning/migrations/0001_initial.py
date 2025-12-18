"""Initial migrations for Phase 1/2 Automation models."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ControlSetting intentionally omitted (not part of the design-aligned net-new app).
        migrations.CreateModel(
            name="Provider",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("driver_class", models.CharField(max_length=255, help_text="Python dotted path to the provider driver class.")),
                ("description", models.TextField(blank=True)),
                ("capabilities", models.JSONField(default=list, blank=True, help_text="List of capability strings (e.g., ['render', 'diff', 'apply']).")),
                ("enabled", models.BooleanField(default=True)),
                ("supported_platforms", models.ManyToManyField(blank=True, related_name="automation_providers", to="dcim.platform")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_provider_set", to="extras.tag")),
            ],
            options={"ordering": ["name"], "verbose_name": "Provider", "verbose_name_plural": "Providers"},
        ),
        migrations.CreateModel(
            name="ProviderConfig",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, help_text="Instance name (e.g., 'prod-dnac', 'campus-cli').")),
                ("enabled", models.BooleanField(default=True)),
                ("settings", models.JSONField(default=dict, blank=True)),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="configs", to="nautobot_network_provisioning.provider")),
                ("secrets_group", models.ForeignKey(blank=True, help_text="Credentials live in Nautobot Secrets; reference a SecretsGroup here.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="extras.secretsgroup")),
                ("scope_locations", models.ManyToManyField(blank=True, related_name="automation_provider_configs", to="dcim.location")),
                ("scope_tenants", models.ManyToManyField(blank=True, related_name="automation_provider_configs", to="tenancy.tenant")),
                ("scope_tags", models.ManyToManyField(blank=True, related_name="automation_provider_configs", to="extras.tag")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_providerconfig_set", to="extras.tag")),
            ],
            options={"ordering": ["provider__name", "name"], "verbose_name": "Provider Config", "verbose_name_plural": "Provider Configs"},
        ),
        migrations.AddConstraint(
            model_name="providerconfig",
            constraint=models.UniqueConstraint(fields=("provider", "name"), name="uniq_providerconfig_provider_name"),
        ),
        migrations.CreateModel(
            name="TaskDefinition",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("category", models.CharField(max_length=100, blank=True)),
                ("input_schema", models.JSONField(default=dict, blank=True)),
                ("output_schema", models.JSONField(default=dict, blank=True)),
                ("documentation", models.TextField(blank=True, help_text="Markdown help text.")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_taskdefinition_set", to="extras.tag")),
            ],
            options={"ordering": ["name"], "verbose_name": "Task", "verbose_name_plural": "Task Catalog"},
        ),
        migrations.CreateModel(
            name="Workflow",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150, unique=True)),
                ("slug", models.SlugField(max_length=160, unique=True)),
                ("description", models.TextField(blank=True)),
                ("category", models.CharField(max_length=100, blank=True)),
                ("version", models.CharField(blank=True, help_text="Optional semantic version.", max_length=50)),
                ("enabled", models.BooleanField(default=True)),
                ("approval_required", models.BooleanField(default=False)),
                ("schedule_allowed", models.BooleanField(default=False)),
                ("input_schema", models.JSONField(default=dict, blank=True)),
                ("default_inputs", models.JSONField(default=dict, blank=True)),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_workflow_set", to="extras.tag")),
            ],
            options={"ordering": ["name"], "verbose_name": "Workflow", "verbose_name_plural": "Workflows"},
        ),
        migrations.CreateModel(
            name="TaskImplementation",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150)),
                ("priority", models.IntegerField(default=100, help_text="Higher wins when multiple implementations match.")),
                ("implementation_type", models.CharField(choices=[("jinja2_config", "Jinja2 Config"), ("jinja2_payload", "Jinja2 Payload"), ("api_call", "API Call"), ("graphql_query", "GraphQL Query"), ("python_hook", "Python Hook")], max_length=32)),
                ("template_content", models.TextField(blank=True, help_text="Jinja2 template or query text (for template-based types).")),
                ("action_config", models.JSONField(default=dict, blank=True, help_text="Config for API calls, hooks, etc.")),
                ("pre_checks", models.JSONField(default=list, blank=True)),
                ("post_checks", models.JSONField(default=list, blank=True)),
                ("enabled", models.BooleanField(default=True)),
                ("manufacturer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="task_implementations", to="dcim.manufacturer")),
                ("platform", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="task_implementations", to="dcim.platform")),
                ("provider_config", models.ForeignKey(blank=True, help_text="Optional override of provider selection for this implementation.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="task_implementations", to="nautobot_network_provisioning.providerconfig")),
                ("software_versions", models.ManyToManyField(blank=True, help_text="Optional: restrict this implementation to specific SoftwareVersion records. Leave empty for all versions.", related_name="task_implementations", to="dcim.softwareversion")),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="implementations", to="nautobot_network_provisioning.taskdefinition")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_taskimplementation_set", to="extras.tag")),
            ],
            options={"ordering": ["task__name", "-priority", "name"], "verbose_name": "Task Implementation", "verbose_name_plural": "Task Implementations"},
        ),
        migrations.CreateModel(
            name="WorkflowStep",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("order", models.PositiveIntegerField(default=0, db_index=True)),
                ("name", models.CharField(max_length=150)),
                ("step_type", models.CharField(choices=[("task", "Task"), ("validation", "Validation"), ("approval", "Approval"), ("notification", "Notification"), ("condition", "Condition"), ("wait", "Wait")], max_length=24)),
                ("input_mapping", models.JSONField(default=dict, blank=True)),
                ("output_mapping", models.JSONField(default=dict, blank=True)),
                ("condition", models.TextField(blank=True, help_text="Jinja2 expression to determine whether this step runs.")),
                ("on_failure", models.CharField(choices=[("stop", "Stop"), ("continue", "Continue"), ("skip_remaining", "Skip Remaining")], default="stop", max_length=24)),
                ("config", models.JSONField(default=dict, blank=True)),
                ("task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workflow_steps", to="nautobot_network_provisioning.taskdefinition")),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="nautobot_network_provisioning.workflow")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_workflowstep_set", to="extras.tag")),
            ],
            options={"ordering": ["workflow__name", "order", "name"], "verbose_name": "Workflow Step", "verbose_name_plural": "Workflow Steps"},
        ),
        migrations.AddConstraint(
            model_name="workflowstep",
            constraint=models.UniqueConstraint(fields=("workflow", "order"), name="uniq_workflowstep_workflow_order"),
        ),
        migrations.CreateModel(
            name="Execution",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("awaiting_approval", "Awaiting Approval"), ("scheduled", "Scheduled"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], db_index=True, default="pending", max_length=32)),
                ("inputs", models.JSONField(default=dict, blank=True)),
                ("context", models.JSONField(default=dict, blank=True)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="automation_executions_approved", to=settings.AUTH_USER_MODEL)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="automation_executions", to=settings.AUTH_USER_MODEL)),
                ("target_devices", models.ManyToManyField(blank=True, related_name="automation_executions", to="dcim.device")),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="executions", to="nautobot_network_provisioning.workflow")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_execution_set", to="extras.tag")),
            ],
            options={"ordering": ["-created"], "verbose_name": "Execution", "verbose_name_plural": "Executions"},
        ),
        migrations.CreateModel(
            name="ExecutionStep",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("order", models.PositiveIntegerField(db_index=True, default=0)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("skipped", "Skipped")], db_index=True, default="pending", max_length=24)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("rendered_content", models.TextField(blank=True)),
                ("inputs", models.JSONField(default=dict, blank=True)),
                ("outputs", models.JSONField(default=dict, blank=True)),
                ("logs", models.TextField(blank=True)),
                ("error_message", models.TextField(blank=True)),
                ("execution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="nautobot_network_provisioning.execution")),
                ("task_implementation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="execution_steps", to="nautobot_network_provisioning.taskimplementation")),
                ("workflow_step", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="execution_steps", to="nautobot_network_provisioning.workflowstep")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_executionstep_set", to="extras.tag")),
            ],
            options={"ordering": ["execution__created", "order"], "verbose_name": "Execution Step", "verbose_name_plural": "Execution Steps"},
        ),
        migrations.AddConstraint(
            model_name="executionstep",
            constraint=models.UniqueConstraint(fields=("execution", "order"), name="uniq_executionstep_execution_order"),
        ),
    ]


