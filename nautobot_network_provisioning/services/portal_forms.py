"""Dynamic Django form builder for RequestForms (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django import forms
from django.contrib.contenttypes.models import ContentType
from nautobot.apps.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField

from nautobot_network_provisioning.models import RequestForm, RequestFormField


@dataclass(frozen=False)
class PortalFieldRenderSpec:
    """Metadata needed to render and enforce conditional visibility in the portal."""

    field_name: str
    label: str
    required: bool
    help_text: str
    depends_on: str | None
    show_condition: str | None
    bound_field: Any = None


def _set_dotted_path(target: dict[str, Any], path: str, value: Any) -> None:
    """Set a dotted path on a nested dict, creating intermediate dicts as needed."""

    parts = [p for p in (path or "").split(".") if p]
    if not parts:
        return
    cur: dict[str, Any] = target
    for key in parts[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[parts[-1]] = value


def map_cleaned_data_to_execution_inputs(*, request_form: RequestForm, cleaned_data: dict[str, Any]) -> dict[str, Any]:
    """Map portal form cleaned_data into Execution.inputs using RequestFormField.map_to.

    Backward-compat behavior:
    - Always include the legacy key at `field_name`
    - If `map_to` is set and differs from `field_name`, also set the mapped path
    """

    inputs: dict[str, Any] = {}
    fields = (
        RequestFormField.objects.filter(form=request_form)
        .only("field_name", "map_to")
        .order_by("order", "field_name")
    )
    for f in fields:
        if f.field_name not in cleaned_data:
            continue
        value = cleaned_data.get(f.field_name)
        # Always keep legacy behavior.
        inputs[f.field_name] = value

        map_to = (f.map_to or "").strip()
        if map_to and map_to != f.field_name:
            _set_dotted_path(inputs, map_to, value)
    return inputs


def _evaluate_show_condition(expr: str, *, inputs: dict[str, Any]) -> bool:
    """Evaluate a Jinja2 expression safely-ish for conditional visibility.

    Expected expressions look like: `input.some_field == "foo"`.
    """

    if not expr or not expr.strip():
        return True
    try:
        from jinja2 import Environment, StrictUndefined  # imported lazily

        env = Environment(undefined=StrictUndefined, autoescape=False)
        compiled = env.compile_expression(expr.strip())
        return bool(compiled(input=inputs))
    except Exception:  # noqa: BLE001 - fail open on expression issues
        # Fail-open in UI/portal to avoid blocking submissions due to expression syntax drift.
        return True


class PortalRequestForm(forms.Form):
    """Build a Django form from RequestForm + RequestFormFields."""

    def __init__(self, *, request_form: RequestForm, data=None, initial=None, **kwargs):
        self.request_form = request_form
        self.render_specs: list[PortalFieldRenderSpec] = []
        super().__init__(data=data, initial=initial or {}, **kwargs)
        self._build_fields()

    def _build_fields(self) -> None:
        fields = (
            RequestFormField.objects.filter(form=self.request_form)
            .select_related("object_type", "depends_on")
            .order_by("order", "field_name")
        )
        for f in fields:
            label = f.label or f.field_name
            help_text = f.help_text or ""
            required = bool(f.required)
            depends_on = getattr(f.depends_on, "field_name", None) if f.depends_on_id else None
            show_condition = (f.show_condition or "").strip() or None

            # --- Low Code Lookup Logic ---
            if f.lookup_type == RequestFormField.LookupTypeChoices.LOCATION_BY_TYPE:
                loc_type_name = f.lookup_config.get("type", "Building")
                f.field_type = RequestFormField.FieldTypeChoices.OBJECT_SELECTOR
                f.object_type = ContentType.objects.get(app_label="dcim", model="location")
                f.queryset_filter = {"location_type__name": loc_type_name}
                if f.lookup_config.get("parent_field"):
                    f.queryset_filter["parent_id"] = f"${f.lookup_config['parent_field']}"
            
            elif f.lookup_type == RequestFormField.LookupTypeChoices.VLAN_BY_TAG:
                f.field_type = RequestFormField.FieldTypeChoices.OBJECT_SELECTOR
                f.object_type = ContentType.objects.get(app_label="ipam", model="vlan")
                tag_prefix = f.lookup_config.get("tag_prefix", "Service:")
                if not f.queryset_filter:
                    f.queryset_filter = {}
                if f.lookup_config.get("tag_field"):
                    f.queryset_filter["tags__name"] = f"{tag_prefix} ${f.lookup_config['tag_field']}"
                if f.lookup_config.get("location_field"):
                    f.queryset_filter["locations"] = f"${f.lookup_config['location_field']}"

            elif f.lookup_type == RequestFormField.LookupTypeChoices.DEVICE_BY_ROLE:
                f.field_type = RequestFormField.FieldTypeChoices.OBJECT_SELECTOR
                f.object_type = ContentType.objects.get(app_label="dcim", model="device")
                role_name = f.lookup_config.get("role")
                if not f.queryset_filter:
                    f.queryset_filter = {}
                if role_name:
                    f.queryset_filter["role__name"] = role_name
                if f.lookup_config.get("location_field"):
                    f.queryset_filter["location"] = f"${f.lookup_config['location_field']}"
            
            elif f.lookup_type == RequestFormField.LookupTypeChoices.TASK_BY_CATEGORY:
                f.field_type = RequestFormField.FieldTypeChoices.OBJECT_SELECTOR
                f.object_type = ContentType.objects.get(app_label="nautobot_network_provisioning", model="taskdefinition")
                cat_name = f.lookup_config.get("category", "Service Catalog")
                f.queryset_filter = {"category": cat_name}

            # --- Field Generation ---
            # If the field is conditionally shown, we treat it as not-required at the field level,
            # then enforce "required when visible" by keeping errors only when visible in clean().
            conditional = bool(depends_on or show_condition)
            required_for_widget = required if not conditional else False

            if f.field_type == RequestFormField.FieldTypeChoices.TEXT:
                self.fields[f.field_name] = forms.CharField(
                    required=required_for_widget,
                    label=label,
                    help_text=help_text,
                    widget=forms.TextInput(attrs={"class": "form-control"}),
                )
            elif f.field_type == RequestFormField.FieldTypeChoices.NUMBER:
                self.fields[f.field_name] = forms.FloatField(
                    required=required_for_widget,
                    label=label,
                    help_text=help_text,
                    widget=forms.NumberInput(attrs={"class": "form-control"}),
                )
            elif f.field_type == RequestFormField.FieldTypeChoices.BOOLEAN:
                self.fields[f.field_name] = forms.BooleanField(required=False, label=label, help_text=help_text)
            elif f.field_type == RequestFormField.FieldTypeChoices.CHOICE:
                choices = [(c, c) for c in (f.choices or [])]
                self.fields[f.field_name] = forms.ChoiceField(
                    required=required_for_widget,
                    label=label,
                    help_text=help_text,
                    choices=choices,
                    widget=forms.Select(attrs={"class": "form-control"}),
                )
            elif f.field_type == RequestFormField.FieldTypeChoices.MULTI_CHOICE:
                choices = [(c, c) for c in (f.choices or [])]
                self.fields[f.field_name] = forms.MultipleChoiceField(
                    required=required_for_widget,
                    label=label,
                    help_text=help_text,
                    choices=choices,
                    widget=forms.SelectMultiple(attrs={"class": "form-control"}),
                )
            elif f.field_type == RequestFormField.FieldTypeChoices.OBJECT_SELECTOR:
                ct: ContentType | None = f.object_type
                if not ct:
                    # Misconfigured field: store raw text as fallback.
                    self.fields[f.field_name] = forms.CharField(
                        required=required_for_widget,
                        label=label,
                        help_text=help_text,
                        widget=forms.TextInput(attrs={"class": "form-control"}),
                    )
                    continue
                model = ct.model_class()
                if not model:
                    self.fields[f.field_name] = forms.CharField(
                        required=required_for_widget,
                        label=label,
                        help_text=help_text,
                        widget=forms.TextInput(attrs={"class": "form-control"}),
                    )
                    continue
                # Default: single-select. Use validation_rules.multi=True to switch to multi-select.
                multi = bool((f.validation_rules or {}).get("multi", False))
                query_params = f.queryset_filter or {}
                
                # Convert $field_name to field_id if needed, or just pass along as Nautobot expects
                # Nautobot's DynamicModelChoiceField handles "$field" syntax natively in query_params.
                
                if multi:
                    self.fields[f.field_name] = DynamicModelMultipleChoiceField(
                        queryset=model.objects.all(),
                        required=required_for_widget,
                        label=label,
                        help_text=help_text,
                        query_params=query_params,
                    )
                else:
                    self.fields[f.field_name] = DynamicModelChoiceField(
                        queryset=model.objects.all(),
                        required=required_for_widget,
                        label=label,
                        help_text=help_text,
                        query_params=query_params,
                    )
            else:
                self.fields[f.field_name] = forms.CharField(
                    required=required_for_widget,
                    label=label,
                    help_text=help_text,
                    widget=forms.TextInput(attrs={"class": "form-control"}),
                )

            # Store render metadata for the template (conditional visibility).
            spec = PortalFieldRenderSpec(
                field_name=f.field_name,
                label=label,
                required=required,
                help_text=help_text,
                depends_on=depends_on,
                show_condition=show_condition,
            )
            spec.bound_field = self[f.field_name]
            self.render_specs.append(spec)

    def clean(self):
        """Drop/ignore hidden conditional fields and enforce required only when visible."""

        cleaned = super().clean() or {}
        inputs_for_eval = dict(cleaned)

        # Compute visibility for each conditional field after base validation.
        for spec in self.render_specs:
            is_conditional = bool(spec.depends_on or spec.show_condition)
            if not is_conditional:
                continue

            visible = True
            if spec.depends_on and not spec.show_condition:
                visible = bool(inputs_for_eval.get(spec.depends_on))
            elif spec.show_condition:
                visible = _evaluate_show_condition(spec.show_condition, inputs=inputs_for_eval)

            if not visible:
                # Hidden: ignore any submitted value and suppress any field-level errors.
                cleaned.pop(spec.field_name, None)
                if spec.field_name in self._errors:
                    del self._errors[spec.field_name]
                continue

            # Visible: if it's marked required, enforce required now (since we made the field not-required).
            if spec.required:
                value = cleaned.get(spec.field_name)
                is_empty = value in (None, "", [], (), {})
                if is_empty:
                    self.add_error(spec.field_name, "This field is required.")

        return cleaned


