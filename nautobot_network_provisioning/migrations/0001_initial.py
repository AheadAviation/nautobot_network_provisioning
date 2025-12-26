"""Initial migrations for Phase 1/2 Automation models."""

from django.conf import settings
from django.db import migrations, models
import django.core.serializers.json
import django.db.models.deletion
import nautobot.core.models.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomationProvider',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('driver_class', models.CharField(help_text="Python path to the driver class (e.g. 'nautobot_network_provisioning.services.providers.netmiko_cli.NetmikoCLIProvider').", max_length=255)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('enabled', models.BooleanField(default=True)),
                ('supported_platforms', models.ManyToManyField(blank=True, related_name='automation_providers', to='dcim.Platform')),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AutomationProviderConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('parameters', models.JSONField(blank=True, help_text='Specific connection parameters (endpoints, options).', null=True)),
                ('enabled', models.BooleanField(default=True)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='configs', to='nautobot_network_provisioning.automationprovider')),
                ('scope_locations', models.ManyToManyField(blank=True, related_name='automation_provider_configs', to='dcim.Location')),
                ('scope_tenants', models.ManyToManyField(blank=True, related_name='automation_provider_configs', to='tenancy.Tenant')),
                ('secrets_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='extras.SecretsGroup')),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TaskIntent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('name', models.CharField(help_text='e.g., Configure VLAN', max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('input_schema', models.JSONField(blank=True, help_text="JSON Schema defining variables this task requires. (e.g., {'vlan_id': 'integer'})", null=True)),
                ('variable_mappings', models.JSONField(blank=True, help_text='Internal mapping definitions for where to find variables in Nautobot (v2.0 Hierarchy).', null=True)),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'Task Intent',
                'verbose_name_plural': 'Task Intents',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('graph_definition', models.JSONField(blank=True, help_text='Node-link structure (React Flow compatible) defining execution order.', null=True)),
                ('enabled', models.BooleanField(default=True)),
                ('approval_required', models.BooleanField(default=False)),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RequestForm',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('published', models.BooleanField(default=True)),
                ('field_definition', models.JSONField(blank=True, help_text='Mapping of form fields to Workflow/Intent variables.', null=True)),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_forms', to='nautobot_network_provisioning.workflow')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TaskImplementation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('priority', models.PositiveIntegerField(default=100, help_text='Higher priority implementation is selected first if multiple match.')),
                ('logic_type', models.CharField(choices=[('jinja2', 'Jinja2 Template'), ('python', 'Python Script')], default='jinja2', max_length=50)),
                ('template_content', models.TextField(blank=True, help_text='The actual code or template content.')),
                ('enabled', models.BooleanField(default=True)),
                ('platform', models.ForeignKey(help_text='Target network platform (e.g., Cisco IOS).', on_delete=django.db.models.deletion.PROTECT, related_name='task_implementations', to='dcim.Platform')),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
                ('task_intent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='implementations', to='nautobot_network_provisioning.taskintent')),
            ],
            options={
                'verbose_name': 'Task Implementation',
                'verbose_name_plural': 'Task Implementations',
                'ordering': ('-priority', 'platform'),
                'unique_together': {('task_intent', 'platform')},
            },
        ),
        migrations.CreateModel(
            name='WorkflowStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.PositiveSmallIntegerField(default=100)),
                ('parameters', models.JSONField(blank=True, help_text='Intent-specific parameters for this workflow step.', null=True)),
                ('task_intent', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='workflow_steps', to='nautobot_network_provisioning.taskintent')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='nautobot_network_provisioning.workflow')),
            ],
            options={
                'ordering': ('workflow', 'weight', 'task_intent'),
                'unique_together': {('workflow', 'weight')},
            },
        ),
        migrations.CreateModel(
            name='TroubleshootingRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('operation_type', models.CharField(choices=[('path_trace', 'Network Path Trace')], default='path_trace', max_length=50)),
                ('object_id', models.UUIDField(blank=True, null=True)),
                ('source_host', models.CharField(max_length=255)),
                ('destination_host', models.CharField(max_length=255)),
                ('result_data', models.JSONField(blank=True, null=True)),
                ('interactive_html', models.TextField(blank=True, help_text='Stored PyVis HTML visualization.')),
                ('start_time', models.DateTimeField(auto_now_add=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('object_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='troubleshooting_records', to='extras.Status')),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='troubleshooting_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Troubleshooting Record',
                'verbose_name_plural': 'Troubleshooting Records',
                'ordering': ('-start_time',),
            },
        ),
        migrations.CreateModel(
            name='RequestFormField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(max_length=100)),
                ('label', models.CharField(blank=True, max_length=100)),
                ('field_type', models.CharField(choices=[('text', 'Text'), ('number', 'Number'), ('boolean', 'Boolean'), ('choice', 'Choice'), ('multi_choice', 'Multi-Choice'), ('object_selector', 'Object Selector (Nautobot Model)')], default='text', max_length=50)),
                ('choices', models.JSONField(blank=True, help_text='List of choices for choice/multi_choice types.', null=True)),
                ('required', models.BooleanField(default=True)),
                ('default', models.CharField(blank=True, max_length=200)),
                ('help_text', models.CharField(blank=True, max_length=200)),
                ('order', models.PositiveSmallIntegerField(default=100)),
                ('show_condition', models.CharField(blank=True, help_text="Jinja2 expression for conditional visibility (e.g. 'input.role == \"access\"').", max_length=200)),
                ('map_to', models.CharField(blank=True, help_text="Dotted path to map this input to in the execution context (e.g. 'vars.vlan_id').", max_length=100)),
                ('sot_loopback', models.BooleanField(default=False, help_text='If true, this field will update a Nautobot model attribute during execution.')),
                ('sot_path', models.CharField(blank=True, help_text="Dotted path to the model attribute (e.g. 'interface.description' or 'device.location').", max_length=100)),
                ('depends_on', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dependents', to='nautobot_network_provisioning.requestformfield')),
                ('form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='nautobot_network_provisioning.requestform')),
                ('object_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('form', 'order', 'field_name'),
                'unique_together': {('form', 'field_name')},
            },
        ),
        migrations.CreateModel(
            name='Execution',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('object_id', models.UUIDField(blank=True, null=True)),
                ('input_data', models.JSONField(blank=True, help_text='The inputs provided at the time of execution.', null=True)),
                ('start_time', models.DateTimeField(auto_now_add=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('object_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType')),
                ('request_form', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='executions', to='nautobot_network_provisioning.requestform')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='executions', to='extras.Status')),
                ('tags', nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='executions', to=settings.AUTH_USER_MODEL)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='executions', to='nautobot_network_provisioning.workflow')),
            ],
            options={
                'ordering': ('-start_time',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ExecutionStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rendered_content', models.TextField(blank=True, help_text='The rendered config or payload.')),
                ('output', models.TextField(blank=True, help_text='Actual output from the device/provider.')),
                ('error_message', models.TextField(blank=True)),
                ('start_time', models.DateTimeField(auto_now_add=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='nautobot_network_provisioning.execution')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='execution_steps', to='extras.Status')),
                ('task_implementation', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='execution_steps', to='nautobot_network_provisioning.taskimplementation')),
            ],
            options={
                'ordering': ('execution', 'start_time'),
            },
        ),
    ]