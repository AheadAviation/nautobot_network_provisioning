"""Provider models (driver types and instance configs) for Automation execution."""

from __future__ import annotations

from django.db import models
from nautobot.apps.models import PrimaryModel
from taggit.managers import TaggableManager


class Provider(PrimaryModel):
    """Provider driver type (e.g., netmiko, napalm, dnac, servicenow)."""

    # Override PrimaryModel.tags to avoid reverse accessor collisions with core models named "Provider" (e.g. circuits.Provider).
    tags = TaggableManager(through="extras.TaggedItem", blank=True, related_name="nautobot_network_provisioning_provider_set")

    name = models.CharField(max_length=100, unique=True)
    driver_class = models.CharField(
        max_length=255,
        help_text="Python dotted path to the provider driver class.",
    )
    description = models.TextField(blank=True)
    capabilities = models.JSONField(
        default=list,
        blank=True,
        help_text="List of capability strings (e.g., ['render', 'diff', 'apply']).",
    )
    supported_platforms = models.ManyToManyField(
        to="dcim.Platform",
        blank=True,
        related_name="automation_providers",
    )
    enabled = models.BooleanField(default=True)

    natural_key_field_names = ["name"]

    class Meta:
        ordering = ["name"]
        verbose_name = "Provider"
        verbose_name_plural = "Providers"

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class ProviderConfig(PrimaryModel):
    """Configured provider instance (scoped config + secrets references)."""

    provider = models.ForeignKey(to=Provider, on_delete=models.PROTECT, related_name="configs")
    name = models.CharField(max_length=100, help_text="Instance name (e.g., 'prod-dnac', 'campus-cli').")
    enabled = models.BooleanField(default=True)

    # Nautobot 2.3+ uses Locations instead of Sites.
    scope_locations = models.ManyToManyField(to="dcim.Location", blank=True, related_name="automation_provider_configs")
    scope_tenants = models.ManyToManyField(to="tenancy.Tenant", blank=True, related_name="automation_provider_configs")
    scope_tags = models.ManyToManyField(to="extras.Tag", blank=True, related_name="automation_provider_configs")

    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Credentials live in Nautobot Secrets; reference a SecretsGroup here.",
    )
    settings = models.JSONField(default=dict, blank=True)

    natural_key_field_names = ["provider", "name"]

    class Meta:
        ordering = ["provider__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "name"], name="uniq_providerconfig_provider_name"),
        ]
        verbose_name = "Provider Config"
        verbose_name_plural = "Provider Configs"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.provider.name}: {self.name}"


