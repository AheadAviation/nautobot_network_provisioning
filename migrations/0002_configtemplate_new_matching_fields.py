# Generated migration for ConfigTemplate model updates and ConfigTemplateHistory

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add new matching fields to ConfigTemplate:
    - manufacturer, platform, software_version FKs
    - effective_date, is_active, superseded_by for date-based versioning
    - Make instance nullable for backward compatibility
    - Make switch_profile nullable for backward compatibility
    
    Also create ConfigTemplateHistory model for automatic version tracking.
    """

    dependencies = [
        # Only depend on our own initial migration - dcim dependency is already in 0001
        ('nautobot_network_provisioning', '0001_initial'),
    ]

    operations = [
        # Make instance field nullable
        migrations.AlterField(
            model_name='configtemplate',
            name='instance',
            field=models.IntegerField(blank=True, null=True, help_text='(Legacy) Groups related template versions together'),
        ),
        
        # Make switch_profile nullable for backward compatibility
        migrations.AlterField(
            model_name='configtemplate',
            name='switch_profile',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='templates',
                to='nautobot_network_provisioning.switchprofile',
                help_text='(Legacy) The switch profile this template is designed for',
            ),
        ),
        
        # Add manufacturer FK
        migrations.AddField(
            model_name='configtemplate',
            name='manufacturer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='config_templates',
                to='dcim.manufacturer',
                help_text='Device manufacturer this template applies to',
            ),
        ),
        
        # Add platform FK
        migrations.AddField(
            model_name='configtemplate',
            name='platform',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='config_templates',
                to='dcim.platform',
                help_text='Platform/OS type this template is designed for',
            ),
        ),
        
        # Add software_version FK
        migrations.AddField(
            model_name='configtemplate',
            name='software_version',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='config_templates',
                to='dcim.softwareversion',
                help_text='Optional: restrict to specific software version',
            ),
        ),
        
        # Add effective_date for date-based versioning
        migrations.AddField(
            model_name='configtemplate',
            name='effective_date',
            field=models.DateField(
                default=django.utils.timezone.now,
                help_text='Date when this template version becomes active',
            ),
        ),
        
        # Add is_active flag
        migrations.AddField(
            model_name='configtemplate',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='Whether this template is currently active and available for use',
            ),
        ),
        
        # Add superseded_by self-reference
        migrations.AddField(
            model_name='configtemplate',
            name='superseded_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='supersedes',
                to='nautobot_network_provisioning.configtemplate',
                help_text='Newer template that replaces this one',
            ),
        ),
        
        # Remove unique_together constraint that references instance/version
        migrations.AlterUniqueTogether(
            name='configtemplate',
            unique_together=set(),
        ),
        
        # Update ordering
        migrations.AlterModelOptions(
            name='configtemplate',
            options={
                'ordering': ['service', 'manufacturer', 'platform', '-effective_date', '-version'],
                'verbose_name': 'Config Template',
                'verbose_name_plural': 'Config Templates',
            },
        ),
        
        # Create ConfigTemplateHistory model
        migrations.CreateModel(
            name='ConfigTemplateHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('template_text', models.TextField(help_text='Snapshot of the template content at this point in time')),
                ('changed_by', models.CharField(help_text='Username who made this change', max_length=100)),
                ('changed_at', models.DateTimeField(auto_now_add=True, help_text='When this change was made')),
                ('change_reason', models.CharField(blank=True, help_text='Optional description of why the change was made', max_length=255)),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='history',
                    to='nautobot_network_provisioning.configtemplate',
                    help_text='The template this history entry belongs to',
                )),
            ],
            options={
                'verbose_name': 'Config Template History',
                'verbose_name_plural': 'Config Template History',
                'ordering': ['-changed_at'],
            },
        ),
    ]
