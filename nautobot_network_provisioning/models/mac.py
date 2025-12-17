"""MAC Address tracking models."""

from django.db import models
from nautobot.apps.models import PrimaryModel
from nautobot.core.models import BaseModel


class MACAddress(PrimaryModel):
    """
    Master record for a MAC address.
    
    This is the central registry of all known MAC addresses with their
    current/last known location and type classification.
    """

    address = models.CharField(
        max_length=17,
        unique=True,
        db_index=True,
        help_text="MAC address in XX:XX:XX:XX:XX:XX format",
    )

    class MACTypeChoices(models.TextChoices):
        INTERFACE = "interface", "Interface MAC"
        ENDPOINT = "endpoint", "Endpoint Device"
        VIRTUAL = "virtual", "Virtual (HSRP/VRRP/VM)"
        UNKNOWN = "unknown", "Unknown"

    mac_type = models.CharField(
        max_length=20,
        choices=MACTypeChoices.choices,
        default=MACTypeChoices.UNKNOWN,
        help_text="Classification of this MAC address",
    )
    vendor = models.CharField(
        max_length=100,
        blank=True,
        help_text="Vendor name derived from OUI lookup",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description or notes",
    )

    # If this is a Nautobot interface's MAC
    assigned_interface = models.OneToOneField(
        to="dcim.Interface",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_mac_address",
        help_text="If this MAC is assigned to a Nautobot-managed interface",
    )

    # Current/last known location (denormalized for fast queries)
    last_device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Last device where this MAC was seen",
    )
    last_interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Last interface where this MAC was seen",
    )
    last_vlan = models.IntegerField(
        null=True,
        blank=True,
        help_text="Last VLAN where this MAC was seen",
    )
    last_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Last known IP address (from ARP)",
    )
    first_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this MAC was first observed",
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this MAC was last observed",
    )

    natural_key_field_names = ["address"]

    class Meta:
        ordering = ["-last_seen"]
        verbose_name = "MAC Address"
        verbose_name_plural = "MAC Addresses"

    def __str__(self):
        return self.address

    def save(self, *args, **kwargs):
        """Normalize MAC address format on save."""
        if self.address:
            # Normalize to uppercase with colons
            self.address = self.address.upper().replace("-", ":")
        super().save(*args, **kwargs)


class MACAddressEntry(BaseModel):
    """
    Current MAC address table entry from a device.
    
    Represents current state - refreshed on each collection.
    This stores the current CAM table entries from network devices.
    """

    mac_address = models.ForeignKey(
        to=MACAddress,
        on_delete=models.CASCADE,
        related_name="current_entries",
        help_text="Reference to the master MAC address record",
    )
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="mac_entries",
        help_text="Device where this MAC was seen",
    )
    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="mac_entries",
        help_text="Interface where this MAC was seen",
    )
    vlan = models.IntegerField(
        null=True,
        blank=True,
        help_text="VLAN where this MAC was learned",
    )

    class EntryTypeChoices(models.TextChoices):
        DYNAMIC = "dynamic", "Dynamic"
        STATIC = "static", "Static"
        SECURE = "secure", "Secure"
        SELF = "self", "Self"

    entry_type = models.CharField(
        max_length=20,
        choices=EntryTypeChoices.choices,
        default=EntryTypeChoices.DYNAMIC,
        help_text="Type of MAC table entry",
    )
    collected_time = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="When this entry was last collected",
    )

    class Meta:
        unique_together = [["mac_address", "device", "interface", "vlan"]]
        verbose_name = "MAC Address Entry"
        verbose_name_plural = "MAC Address Entries"

    def __str__(self):
        return f"{self.mac_address} on {self.device}:{self.interface}"


class MACAddressHistory(BaseModel):
    """
    Historical record of MAC address sightings.
    
    Retained for 30 days, then archived/deleted by the archiver job.
    """

    mac_address = models.ForeignKey(
        to=MACAddress,
        on_delete=models.CASCADE,
        related_name="history",
        help_text="Reference to the master MAC address record",
    )
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="mac_history",
        help_text="Device where this MAC was seen",
    )
    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="mac_history",
        help_text="Interface where this MAC was seen",
    )
    vlan = models.IntegerField(
        null=True,
        blank=True,
        help_text="VLAN where this MAC was learned",
    )
    entry_type = models.CharField(
        max_length=20,
        default="dynamic",
        help_text="Type of MAC table entry",
    )

    first_seen = models.DateTimeField(
        db_index=True,
        help_text="When this MAC was first seen at this location",
    )
    last_seen = models.DateTimeField(
        db_index=True,
        help_text="When this MAC was last seen at this location",
    )
    sighting_count = models.IntegerField(
        default=1,
        help_text="Number of times seen at this location during this period",
    )

    class Meta:
        ordering = ["-last_seen"]
        verbose_name = "MAC Address History"
        verbose_name_plural = "MAC Address History"

    def __str__(self):
        return f"{self.mac_address} on {self.device}:{self.interface} ({self.first_seen} - {self.last_seen})"
