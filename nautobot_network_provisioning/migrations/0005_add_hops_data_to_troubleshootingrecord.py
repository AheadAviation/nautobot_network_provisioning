# Generated migration to add hops_data field to TroubleshootingRecord

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nautobot_network_provisioning', '0004_rename_task_implementation_to_task_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='troubleshootingrecord',
            name='hops_data',
            field=models.JSONField(blank=True, help_text='Incremental hop data for real-time visualization during trace execution.', null=True),
        ),
    ]

