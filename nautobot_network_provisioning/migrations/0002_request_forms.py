from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_network_provisioning", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="RequestForm",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150, unique=True)),
                ("slug", models.SlugField(max_length=160, unique=True)),
                ("description", models.TextField(blank=True)),
                ("category", models.CharField(blank=True, max_length=100)),
                ("icon", models.CharField(blank=True, help_text="Optional icon name (UI hint).", max_length=100)),
                ("published", models.BooleanField(default=False)),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="request_forms", to="nautobot_network_provisioning.workflow")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_requestform_set", to="extras.tag")),
            ],
            options={"ordering": ["name"], "verbose_name": "Request Form", "verbose_name_plural": "Request Forms"},
        ),
        migrations.CreateModel(
            name="RequestFormField",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("order", models.PositiveIntegerField(db_index=True, default=0)),
                ("field_name", models.CharField(help_text="Internal name; also used as the key in Execution.inputs by default.", max_length=100)),
                ("field_type", models.CharField(choices=[("object_selector", "Object Selector"), ("text", "Text"), ("number", "Number"), ("choice", "Choice"), ("multi_choice", "Multi Choice"), ("boolean", "Boolean")], max_length=24)),
                ("label", models.CharField(max_length=150)),
                ("help_text", models.TextField(blank=True)),
                ("required", models.BooleanField(default=False)),
                ("default_value", models.JSONField(blank=True, default=dict)),
                ("validation_rules", models.JSONField(blank=True, default=dict)),
                ("choices", models.JSONField(blank=True, default=list, help_text="For choice/multi_choice fields.")),
                ("queryset_filter", models.JSONField(blank=True, default=dict, help_text="Optional queryset filter (JSON).")),
                ("show_condition", models.TextField(blank=True, help_text="Jinja2 expression for conditional visibility.")),
                ("map_to", models.CharField(blank=True, help_text="Optional dotted path to map into Execution.inputs (defaults to field_name).", max_length=200)),
                ("depends_on", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dependents", to="nautobot_network_provisioning.requestformfield")),
                ("form", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fields", to="nautobot_network_provisioning.requestform")),
                ("object_type", models.ForeignKey(blank=True, help_text="For object selectors: the target object type (e.g., dcim.device).", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="contenttypes.contenttype")),
                ("tags", models.ManyToManyField(blank=True, related_name="nautobot_network_provisioning_requestformfield_set", to="extras.tag")),
            ],
            options={"ordering": ["form__name", "order", "field_name"], "verbose_name": "Request Form Field", "verbose_name_plural": "Request Form Fields"},
        ),
        migrations.AddConstraint(
            model_name="requestformfield",
            constraint=models.UniqueConstraint(fields=("form", "order"), name="uniq_requestformfield_form_order"),
        ),
        migrations.AddConstraint(
            model_name="requestformfield",
            constraint=models.UniqueConstraint(fields=("form", "field_name"), name="uniq_requestformfield_form_field_name"),
        ),
    ]


