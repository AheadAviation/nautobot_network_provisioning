"""Work Queue model for scheduled port configuration changes."""

from django.db import models
from nautobot.apps.models import PrimaryModel


class WorkQueueEntry(PrimaryModel):
    """
    A scheduled port configuration change request.
    
    This replaces the TWIX `workqueue` table.
    """

    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    # Target device/interface
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.PROTECT,
        related_name="work_queue_entries",
        help_text="Target device for the configuration change",
    )
    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.PROTECT,
        related_name="work_queue_entries",
        help_text="Target interface for the configuration change",
    )

    # Original lookup context (for reference/audit)
    building = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Building where the jack is located (for audit)",
    )
    comm_room = models.CharField(
        max_length=50,
        blank=True,
        help_text="Communications room (for audit)",
    )
    jack = models.CharField(
        max_length=50,
        blank=True,
        help_text="Jack identifier (for audit)",
    )

    # Configuration to apply
    service = models.ForeignKey(
        to="nautobot_network_provisioning.PortService",
        on_delete=models.PROTECT,
        related_name="work_queue_entries",
        help_text="The port service/template type to apply",
    )
    template = models.ForeignKey(
        to="nautobot_network_provisioning.ConfigTemplate",
        on_delete=models.PROTECT,
        related_name="work_queue_entries",
        help_text="The specific template to use",
    )
    vlan = models.IntegerField(
        null=True,
        blank=True,
        help_text="Optional VLAN override",
    )

    # Scheduling
    scheduled_time = models.DateTimeField(
        db_index=True,
        help_text="When to apply this configuration",
    )
    attempted_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the last attempt was made",
    )
    completed_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the configuration was successfully applied",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,
        help_text="Current status of this work queue entry",
    )
    status_message = models.TextField(
        blank=True,
        help_text="Status message or error details",
    )

    # Config backup (before change)
    previous_config = models.TextField(
        blank=True,
        help_text="Interface config before the change was applied",
    )
    applied_config = models.TextField(
        blank=True,
        help_text="Actual config that was pushed",
    )

    # Audit
    requested_by = models.CharField(
        max_length=100,
        help_text="Username who requested this change",
    )
    request_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the requester",
    )

    class Meta:
        ordering = ["-scheduled_time"]
        verbose_name = "Work Queue Entry"
        verbose_name_plural = "Work Queue Entries"

    def __str__(self):
        device_name = self.device.name if self.device else "Unknown"
        interface_name = self.interface.name if self.interface else "Unknown"
        service_name = self.service.name if self.service else "Unknown"
        return f"{device_name}:{interface_name} - {service_name} ({self.status})"
