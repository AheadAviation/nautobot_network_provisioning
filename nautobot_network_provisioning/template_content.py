from nautobot.apps.ui import TemplateExtension

class DeviceIntentButtons(TemplateExtension):
    """
    Injects 'Run Task' and 'Intent Status' buttons into the Device detail view.
    """
    model = "dcim.device"

    def buttons(self):
        from .models import RequestForm, Execution
        # We can dynamically determine which tasks are available for this device
        device = self.context["object"]
        from .models import RequestForm, RequestFormField
        from django.contrib.contenttypes.models import ContentType
        
        device_ct = ContentType.objects.get_for_model(device)
        
        # Find request forms that have an object selector for Device
        applicable_forms = RequestForm.objects.filter(
            published=True,
            fields__field_type="object_selector",
            fields__object_type=device_ct
        ).distinct()

        applicable_forms_data = []
        for rf in applicable_forms:
            field = rf.fields.filter(field_type="object_selector", object_type=device_ct).first()
            applicable_forms_data.append({
                "form": rf,
                "field_name": field.field_name if field else None
            })
        
        return self.render("nautobot_network_provisioning/inc/device_buttons.html", {
            "device": device,
            "applicable_forms": applicable_forms_data,
        })

    def right_page(self):
        from .models import Execution
        # Injects the 'Intent Status' panel or 'Flight Recorder' history
        device = self.context["object"]
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(device)
        recent_executions = Execution.objects.filter(
            object_type=ct,
            object_id=device.pk
        ).order_by("-start_time")[:5]
        
        return self.render("nautobot_network_provisioning/inc/device_intent_panel.html", {
            "device": device,
            "recent_executions": recent_executions,
        })

    def detail_tabs(self):
        device = self.context["object"]
        from django.urls import reverse
        return [
            {
                "title": "Troubleshooting",
                "url": reverse("plugins:nautobot_network_provisioning:troubleshooting", kwargs={
                    "model_label": "dcim.device",
                    "pk": device.pk
                }),
            },
        ]

class InterfaceIntentButtons(TemplateExtension):
    """
    Injects 'Change Port' actions into the Interface detail view.
    """
    model = "dcim.interface"

    def buttons(self):
        interface = self.context["object"]
        from .models import RequestForm, RequestFormField
        from django.contrib.contenttypes.models import ContentType
        
        interface_ct = ContentType.objects.get_for_model(interface)
        
        # Find request forms that have an object selector for Interface
        applicable_forms = RequestForm.objects.filter(
            published=True,
            fields__field_type="object_selector",
            fields__object_type=interface_ct
        ).distinct()

        applicable_forms_data = []
        for rf in applicable_forms:
            field = rf.fields.filter(field_type="object_selector", object_type=interface_ct).first()
            applicable_forms_data.append({
                "form": rf,
                "field_name": field.field_name if field else None
            })
        
        return self.render("nautobot_network_provisioning/inc/interface_buttons.html", {
            "interface": interface,
            "applicable_forms": applicable_forms_data,
        })

    def detail_tabs(self):
        interface = self.context["object"]
        from django.urls import reverse
        return [
            {
                "title": "Troubleshooting",
                "url": reverse("plugins:nautobot_network_provisioning:troubleshooting", kwargs={
                    "model_label": "dcim.interface",
                    "pk": interface.pk
                }),
            },
        ]

template_extensions = [DeviceIntentButtons, InterfaceIntentButtons]

