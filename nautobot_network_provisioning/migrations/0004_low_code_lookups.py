from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('nautobot_network_provisioning', '0003_add_custom_field_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestformfield',
            name='lookup_type',
            field=models.CharField(choices=[('manual', 'Manual JSON Filter'), ('location_by_type', 'Location by Type'), ('vlan_by_tag', 'VLAN by Tag'), ('device_by_role', 'Device by Role'), ('task_by_category', 'Task by Category')], default='manual', help_text='Simplified lookup logic for this field.', max_length=32),
        ),
        migrations.AddField(
            model_name='requestformfield',
            name='lookup_config',
            field=models.JSONField(blank=True, default=dict, help_text='Configuration for the simplified lookup.'),
        ),
    ]
