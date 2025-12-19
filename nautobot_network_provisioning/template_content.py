from nautobot.apps.ui import TemplateExtension
from django.urls import reverse
from nautobot_network_provisioning.models import TaskImplementation, TaskDefinition, Workflow, RequestForm

class TaskImplementationIDEButton(TemplateExtension):
    model = "nautobot_network_provisioning.taskimplementation"

    def detail_buttons(self):
        return [
            {
                "link": reverse("plugins:nautobot_network_provisioning:template_ide", kwargs={"pk": self.context["object"].pk}),
                "title": "Open in IDE",
                "icon_class": "mdi mdi-code-braces",
                "button_class": "btn btn-info",
            }
        ]

class TaskDefinitionImplementations(TemplateExtension):
    model = "nautobot_network_provisioning.taskdefinition"

    def right_column(self):
        # Show list of implementations for this task
        return self.render("nautobot_network_provisioning/inc/task_implementations_table.html")

    def left_column(self):
        # Show workflow steps using this task
        return self.render("nautobot_network_provisioning/inc/task_usage_table.html")

class WorkflowSteps(TemplateExtension):
    model = "nautobot_network_provisioning.workflow"

    def full_width_page(self):
        # Show steps in a full-width panel
        return self.render("nautobot_network_provisioning/inc/workflow_steps_table.html")

    def extra_tabs(self):
        return [
            {
                "title": "Designer",
                "url": reverse("plugins:nautobot_network_provisioning:workflow_designer", kwargs={"pk": self.context["object"].pk}),
            }
        ]

class RequestFormFields(TemplateExtension):
    model = "nautobot_network_provisioning.requestform"

    def full_width_page(self):
        return self.render("nautobot_network_provisioning/inc/request_form_fields_table.html")
    
    def extra_tabs(self):
        return [
            {
                "title": "Form Builder",
                "url": reverse("plugins:nautobot_network_provisioning:requestform_builder", kwargs={"pk": self.context["object"].pk}),
            }
        ]

template_extensions = [TaskImplementationIDEButton, TaskDefinitionImplementations, WorkflowSteps, RequestFormFields]
