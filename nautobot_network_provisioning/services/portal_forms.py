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
    """Map portal form cleaned_data into Execution.inputs using RequestFormField.map_to."""
    inputs: dict[str, Any] = {}
    fields = RequestFormField.objects.filter(form=request_form)
    
    for f in fields:
        if f.field_name not in cleaned_data:
            continue
        value = cleaned_data.get(f.field_name)
        
        # Default: use field name
        inputs[f.field_name] = value

        # Mapping: use dotted path if provided
        map_to = (f.map_to or "").strip()
        if map_to and map_to != f.field_name:
            _set_dotted_path(inputs, map_to, value)
    return inputs


class PortalRequestForm(forms.Form):
    """Build a Django form from RequestForm + RequestFormFields."""

    def __init__(self, *, request_form: RequestForm, data=None, initial=None, **kwargs):
        self.request_form = request_form
        self.render_specs: list[PortalFieldRenderSpec] = []
        super().__init__(data=data, initial=initial or {}, **kwargs)
        self._build_fields()
        
        # System fields
        self.fields["__dry_run"] = forms.BooleanField(
            required=False, 
            label="Dry Run", 
            help_text="If checked, only a preview will be generated.",
            initial=True
        )

    def _build_fields(self) -> None:
        fields = RequestFormField.objects.filter(form=self.request_form).order_by("order", "field_name")
        for f in fields:
            label = f.label or f.field_name
            help_text = f.help_text or ""
            required = bool(f.required)
            depends_on = f.depends_on.field_name if f.depends_on else None
            show_condition = (f.show_condition or "").strip() or None

            # Conditional fields are not required at the widget level;
            # we enforce "required when visible" in clean().
            conditional = bool(depends_on or show_condition)
            required_for_widget = required if not conditional else False

            if f.field_type == "text":
                self.fields[f.field_name] = forms.CharField(
                    required=required_for_widget, label=label, help_text=help_text,
                    widget=forms.TextInput(attrs={"class": "form-control"})
                )
            elif f.field_type == "number":
                self.fields[f.field_name] = forms.FloatField(
                    required=required_for_widget, label=label, help_text=help_text,
                    widget=forms.NumberInput(attrs={"class": "form-control"})
                )
            elif f.field_type == "boolean":
                self.fields[f.field_name] = forms.BooleanField(required=False, label=label, help_text=help_text)
            elif f.field_type == "choice":
                choices = [(c, c) for c in (f.choices or [])]
                self.fields[f.field_name] = forms.ChoiceField(
                    required=required_for_widget, label=label, help_text=help_text, choices=choices,
                    widget=forms.Select(attrs={"class": "form-control"})
                )
            elif f.field_type == "object_selector":
                model = f.object_type.model_class() if f.object_type else None
                if model:
                    self.fields[f.field_name] = DynamicModelChoiceField(
                        queryset=model.objects.all(), required=required_for_widget, label=label, help_text=help_text
                    )
                else:
                    self.fields[f.field_name] = forms.CharField(required=required_for_widget, label=label, help_text=help_text)

            # Store metadata for template
            spec = PortalFieldRenderSpec(
                field_name=f.field_name, label=label, required=required, help_text=help_text,
                depends_on=depends_on, show_condition=show_condition
            )
            spec.bound_field = self[f.field_name]
            self.render_specs.append(spec)

