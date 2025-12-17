"""ARP Entry model for IP-to-MAC mappings."""

from django.db import models
from nautobot.core.models import BaseModel


class ARPEntry(BaseModel):
    """
    ARP table entry mapping IP to MAC.
    
    Stores current ARP table entries from network devices,
    providing IP-to-MAC address resolution.
    """

    mac_address = models.ForeignKey(
        to="nautobot_network_provisioning.MACAddress",
        on_delete=models.CASCADE,
        related_name="arp_entries",
        help_text="Reference to the master MAC address record",
    )
    ip_address = models.GenericIPAddressField(
        db_index=True,
        help_text="IP address from the ARP table",
    )
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="arp_entries",
        help_text="Device where this ARP entry was learned",
    )
    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arp_entries",
        help_text="Interface where this ARP entry was learned (if available)",
    )
    vrf = models.CharField(
        max_length=100,
        blank=True,
        default="default",
        help_text="VRF context for this ARP entry",
    )

    class EntryTypeChoices(models.TextChoices):
        DYNAMIC = "dynamic", "Dynamic"
        STATIC = "static", "Static"
        INCOMPLETE = "incomplete", "Incomplete"

    entry_type = models.CharField(
        max_length=20,
        choices=EntryTypeChoices.choices,
        default=EntryTypeChoices.DYNAMIC,
        help_text="Type of ARP entry",
    )
    collected_time = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="When this entry was last collected",
    )

    class Meta:
        unique_together = [["ip_address", "device", "vrf"]]
        verbose_name = "ARP Entry"
        verbose_name_plural = "ARP Entries"

    def __str__(self):
        return f"{self.ip_address} -> {self.mac_address} on {self.device}"
