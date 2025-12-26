from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from nautobot.core.models.generics import PrimaryModel
from nautobot.apps.models import StatusField

User = get_user_model()


class TroubleshootingRecord(PrimaryModel):
    """Record of a troubleshooting operation (e.g. Network Path Trace)."""

    operation_type = models.CharField(
        max_length=50,
        choices=(
            ("path_trace", "Network Path Trace"),
        ),
        default="path_trace",
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name="troubleshooting_records",
        blank=True,
        null=True,
    )
    # Generic foreign key to the source object
    object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        related_name="+",
        blank=True,
        null=True,
    )
    object_id = models.UUIDField(blank=True, null=True)
    target_object = GenericForeignKey("object_type", "object_id")

    status = StatusField(related_name="troubleshooting_records")
    
    # Input parameters
    source_host = models.CharField(max_length=255)
    destination_host = models.CharField(max_length=255)
    
    # Results
    result_data = models.JSONField(blank=True, null=True)
    interactive_html = models.TextField(blank=True, help_text="Stored PyVis HTML visualization.")
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-start_time",)
        verbose_name = "Troubleshooting Record"
        verbose_name_plural = "Troubleshooting Records"

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.start_time}"

