"""Jack Mapping model for Building/Room/Jack to Device/Interface lookup."""

from django.db import models
from nautobot.apps.models import PrimaryModel


class JackMapping(PrimaryModel):
    """
    Maps a physical jack (Building + Comm Room + Jack ID) to a switch interface.
    
    This enables the Building/Room/Jack lookup from the original TWIX system,
    replacing the NetDisco `portinfo` table query.
    """

    # Location identifiers
    building = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="jack_mappings",
        help_text="Building location",
    )
    comm_room = models.CharField(
        max_length=50,
        help_text="Communications room identifier (e.g., '040', 'MDF-1')",
    )
    jack = models.CharField(
        max_length=50,
        help_text="Jack identifier (e.g., '0228', 'A-101')",
    )

    # Target switch interface
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.PROTECT,
        related_name="jack_mappings",
        help_text="The switch this jack connects to",
    )
    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.PROTECT,
        related_name="jack_mapping",
        help_text="The interface on the switch",
    )

    # Optional metadata
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional description or notes",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this mapping is currently active",
    )

    natural_key_field_names = ["building", "comm_room", "jack"]

    class Meta:
        ordering = ["building", "comm_room", "jack"]
        unique_together = [["building", "comm_room", "jack"]]
        verbose_name = "Jack Mapping"
        verbose_name_plural = "Jack Mappings"
        constraints = [
            models.UniqueConstraint(
                fields=["interface"],
                name="unique_interface_jack_mapping",
            )
        ]

    def __str__(self):
        building_name = self.building.name if self.building else "Unknown"
        device_name = self.device.name if self.device else "Unknown"
        interface_name = self.interface.name if self.interface else "Unknown"
        return f"{building_name}/{self.comm_room}/{self.jack} -> {device_name}:{interface_name}"
