"""Migration to add ManyToMany software_versions field to ConfigTemplate."""

from django.db import migrations, models


def migrate_software_version_to_m2m(apps, schema_editor):
    """
    Migrate existing software_version FK data to the new software_versions M2M field.
    """
    ConfigTemplate = apps.get_model('nautobot_network_provisioning', 'ConfigTemplate')
    
    for template in ConfigTemplate.objects.filter(software_version__isnull=False):
        template.software_versions.add(template.software_version)


def reverse_migrate_m2m_to_fk(apps, schema_editor):
    """
    Reverse migration - take first version from M2M and set as FK.
    """
    ConfigTemplate = apps.get_model('nautobot_network_provisioning', 'ConfigTemplate')
    
    for template in ConfigTemplate.objects.all():
        first_version = template.software_versions.first()
        if first_version:
            template.software_version = first_version
            template.save()


class Migration(migrations.Migration):

    dependencies = [
        ('nautobot_network_provisioning', '0002_configtemplate_new_matching_fields'),
    ]

    operations = [
        # Add the new ManyToMany field
        migrations.AddField(
            model_name='configtemplate',
            name='software_versions',
            field=models.ManyToManyField(
                blank=True,
                help_text='Software versions this template applies to (leave empty for all versions)',
                related_name='config_templates',
                to='dcim.softwareversion',
            ),
        ),
        # Migrate data from the old FK to the new M2M
        migrations.RunPython(migrate_software_version_to_m2m, reverse_migrate_m2m_to_fk),
        # Update the old FK field to remove the related_name conflict
        migrations.AlterField(
            model_name='configtemplate',
            name='software_version',
            field=models.ForeignKey(
                blank=True,
                help_text='(Deprecated) Use software_versions instead',
                null=True,
                on_delete=models.SET_NULL,
                related_name='+',
                to='dcim.softwareversion',
            ),
        ),
    ]
