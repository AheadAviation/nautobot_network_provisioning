"""Add Folder model and folder fields to TaskIntent, Workflow, and RequestForm."""

from django.db import migrations, models
import django.core.serializers.json
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('nautobot_network_provisioning', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('_custom_field_data', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('name', models.CharField(help_text='Folder name (e.g., Campus_Ops)', max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, help_text='Folder description and purpose')),
                ('parent', models.ForeignKey(blank=True, help_text='Parent folder for hierarchical organization', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='nautobot_network_provisioning.folder')),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'verbose_name': 'Folder',
                'verbose_name_plural': 'Folders',
                'ordering': ('name',),
            },
        ),
        migrations.AddField(
            model_name='taskintent',
            name='folder',
            field=models.ForeignKey(blank=True, help_text='Folder for organization in Catalog Explorer', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='nautobot_network_provisioning.folder'),
        ),
        migrations.AddField(
            model_name='workflow',
            name='folder',
            field=models.ForeignKey(blank=True, help_text='Folder for organization in Catalog Explorer', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workflows', to='nautobot_network_provisioning.folder'),
        ),
        migrations.AddField(
            model_name='requestform',
            name='folder',
            field=models.ForeignKey(blank=True, help_text='Folder for organization in Catalog Explorer', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forms', to='nautobot_network_provisioning.folder'),
        ),
    ]

