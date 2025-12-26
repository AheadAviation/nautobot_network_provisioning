# Generated migration to rename ExecutionStep.task_implementation to task_strategy

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nautobot_network_provisioning', '0003_taskstrategy_alter_taskintent_options_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='executionstep',
            old_name='task_implementation',
            new_name='task_strategy',
        ),
    ]

