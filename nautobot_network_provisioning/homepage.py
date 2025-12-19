from nautobot.apps.ui import HomePagePanel, HomePageItem
from nautobot_network_provisioning.models import Execution, Workflow, TaskDefinition

class AutomationSummaryPanel(HomePagePanel):
    name = "Network Automation Summary"
    weight = 100
    permissions = []
    
    def render(self):
        execution_count = Execution.objects.count()
        workflow_count = Workflow.objects.filter(enabled=True).count()
        task_count = TaskDefinition.objects.count()
        
        return self.render_to_html({
            "execution_count": execution_count,
            "workflow_count": workflow_count,
            "task_count": task_count,
        })

layout = [
    AutomationSummaryPanel(name="Network Automation Summary"),
]
