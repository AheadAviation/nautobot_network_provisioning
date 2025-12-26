from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from nautobot_network_provisioning.models import Execution, RequestForm
from .services.portal_forms import PortalRequestForm, map_cleaned_data_to_execution_inputs


class PortalView(View):
    """List all published Request Forms (The Box Covers)."""
    template_name = "nautobot_network_provisioning/portal.html"

    def get(self, request):
        forms = RequestForm.objects.filter(published=True).order_by("name")
        return render(request, self.template_name, {"forms": forms})


class PortalRequestFormView(View):
    """Render and process a specific Request Form."""
    template_name = "nautobot_network_provisioning/portal_request_form.html"

    def get(self, request, slug: str):
        rf = get_object_or_404(RequestForm, slug=slug, published=True)
        # Pass request.GET as initial data
        form = PortalRequestForm(request_form=rf, initial=request.GET.dict())
        return render(request, self.template_name, {"request_form": rf, "form": form})

    def post(self, request, slug: str):
        rf = get_object_or_404(RequestForm, slug=slug, published=True)
        form = PortalRequestForm(request_form=rf, data=request.POST)
        
        if not form.is_valid():
            return render(request, self.template_name, {"request_form": rf, "form": form})

        # Map cleaned data to execution inputs
        inputs = map_cleaned_data_to_execution_inputs(request_form=rf, cleaned_data=form.cleaned_data)
        
        # Determine target_object from the form inputs
        target_obj = None
        for field in rf.fields.filter(field_type="object_selector"):
            val = form.cleaned_data.get(field.field_name)
            if val:
                target_obj = val
                break

        from nautobot.extras.models import Status
        pending_status = Status.objects.get_for_model(Execution).get(slug="pending")

        # Create Execution (Audit Trail)
        exe = Execution.objects.create(
            workflow=rf.workflow,
            request_form=rf,
            user=request.user,
            status=pending_status,
            input_data=inputs,
            target_object=target_obj,
        )

        messages.success(request, f"Request submitted. Execution {exe.pk} created.")
        return redirect("plugins:nautobot_network_provisioning:execution", pk=exe.pk)

