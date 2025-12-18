from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_network_provisioning", "0002_request_forms"),
    ]

    operations = [
        migrations.AddField(
            model_name="provider",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="providerconfig",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="taskdefinition",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="taskimplementation",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="workflow",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="workflowstep",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="execution",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="executionstep",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="requestform",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="requestformfield",
            name="_custom_field_data",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]


