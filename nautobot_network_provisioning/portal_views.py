"""Phase 3: Self-service Portal views."""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from nautobot_network_provisioning.models import Execution, RequestForm
from nautobot_network_provisioning.services.portal_forms import PortalRequestForm, map_cleaned_data_to_execution_inputs


def _serialize_value(v):
    if hasattr(v, "pk"):
        return str(v.pk)
    if hasattr(v, "all"):
        # QuerySet-like
        return [_serialize_value(x) for x in v.all()]
    if isinstance(v, dict):
        return {k: _serialize_value(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_serialize_value(x) for x in v]
    return v


def _extract_target_device_ids(*, request_form: RequestForm, cleaned_data: dict) -> list[str]:
    """Best-effort device target selection using field definitions and related objects."""

    device_ids: set[str] = set()

    # Import lazily to avoid Nautobot app loading issues.
    from nautobot.dcim.models import Device, Interface

    fields = (
        request_form.fields.select_related("object_type")
        .only("field_name", "field_type", "object_type")
        .order_by("order", "field_name")
    )
    for f in fields:
        if f.field_type != "object_selector":
            continue

        ct = f.object_type
        model = ct.model_class() if ct else None
        if not model:
            continue
        if f.field_name not in cleaned_data:
            continue

        value = cleaned_data.get(f.field_name)

        def iter_values(val):
            if val is None:
                return []
            if hasattr(val, "all"):
                return list(val.all())
            if isinstance(val, (list, tuple)):
                return list(val)
            return [val]

        for obj in iter_values(value):
            if isinstance(obj, Device):
                device_ids.add(str(obj.pk))
            elif isinstance(obj, Interface) and getattr(obj, "device_id", None):
                device_ids.add(str(obj.device_id))
            else:
                # Generic fallback: objects with `.device` FK.
                dev = getattr(obj, "device", None)
                dev_id = getattr(obj, "device_id", None)
                if isinstance(dev, Device):
                    device_ids.add(str(dev.pk))
                elif dev_id:
                    device_ids.add(str(dev_id))

    return sorted(device_ids)


class PortalView(View):
    template_name = "nautobot_network_provisioning/portal.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")
        forms = RequestForm.objects.filter(published=True).select_related("workflow").order_by("name")
        return render(request, self.template_name, {"forms": forms})


class PortalRequestFormView(View):
    template_name = "nautobot_network_provisioning/portal_request_form.html"

    def get(self, request, slug: str):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        rf = get_object_or_404(RequestForm, slug=slug, published=True)
        form = PortalRequestForm(request_form=rf)
        fields = rf.fields.select_related("depends_on").order_by("order", "field_name")
        return render(request, self.template_name, {"request_form": rf, "form": form, "fields": fields})

    def post(self, request, slug: str):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        rf = get_object_or_404(RequestForm, slug=slug, published=True)
        form = PortalRequestForm(request_form=rf, data=request.POST)
        if not form.is_valid():
            fields = rf.fields.select_related("depends_on").order_by("order", "field_name")
            return render(request, self.template_name, {"request_form": rf, "form": form, "fields": fields})

        # Build execution inputs honoring `map_to` dotted paths.
        mapped_inputs = map_cleaned_data_to_execution_inputs(request_form=rf, cleaned_data=form.cleaned_data or {})
        inputs = {k: _serialize_value(v) for k, v in (mapped_inputs or {}).items()}
        exe = Execution.objects.create(
            workflow=rf.workflow,
            requested_by=request.user,
            status=Execution.StatusChoices.PENDING,
            inputs=inputs,
        )

        # Better target selection: use object selector fields and derive devices from interfaces, etc.
        from nautobot.dcim.models import Device

        device_ids = _extract_target_device_ids(request_form=rf, cleaned_data=form.cleaned_data or {})
        if device_ids:
            exe.target_devices.set(Device.objects.filter(pk__in=device_ids))

        messages.success(request, "Request submitted. Execution created.")
        return redirect("plugins:nautobot_network_provisioning:execution", pk=exe.pk)


