from django.db import models
from nautobot.core.models.generics import PrimaryModel


class Folder(PrimaryModel):
    """
    Hierarchical folder structure for organizing Tasks, Workflows, and Forms.
    Enables the Catalog Explorer tree browser.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Folder name (e.g., Campus_Ops)")
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, help_text="Folder description and purpose")
    parent = models.ForeignKey(
        to='self',
        on_delete=models.CASCADE,
        related_name='children',
        blank=True,
        null=True,
        help_text="Parent folder for hierarchical organization"
    )
    
    class Meta:
        ordering = ("name",)
        verbose_name = "Folder"
        verbose_name_plural = "Folders"
    
    def __str__(self):
        return self.name
    
    def get_path(self):
        """Return the full path of this folder (e.g., 'Campus_Ops/Network_Config')"""
        if self.parent:
            return f"{self.parent.get_path()}/{self.name}"
        return self.name
    
    def get_children_count(self):
        """Return count of direct children folders"""
        return self.children.count()
    
    def get_items_count(self):
        """Return total count of items (tasks, workflows, forms) in this folder"""
        # Use string references to avoid circular imports
        from django.apps import apps
        TaskIntent = apps.get_model('nautobot_network_provisioning', 'TaskIntent')
        Workflow = apps.get_model('nautobot_network_provisioning', 'Workflow')
        RequestForm = apps.get_model('nautobot_network_provisioning', 'RequestForm')
        
        tasks = TaskIntent.objects.filter(folder=self).count()
        workflows = Workflow.objects.filter(folder=self).count()
        forms = RequestForm.objects.filter(folder=self).count()
        return tasks + workflows + forms

