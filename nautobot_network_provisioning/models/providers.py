from django.db import models
from nautobot.core.models.generics import PrimaryModel, OrganizationalModel
from nautobot.dcim.models import Platform, Location
from nautobot.tenancy.models import Tenant
from nautobot.extras.models import SecretsGroup


class AutomationProvider(PrimaryModel):
    """An external automation system (Netmiko, NAPALM, DNAC)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    driver_class = models.CharField(
        max_length=255,
        help_text="Python path to the driver class (e.g. 'nautobot_network_provisioning.services.providers.netmiko_cli.NetmikoCLIProvider').",
    )
    supported_platforms = models.ManyToManyField(
        to=Platform,
        related_name="automation_providers",
        blank=True,
    )
    description = models.CharField(max_length=200, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class AutomationProviderConfig(PrimaryModel):
    """A specific instance/configuration of a provider (e.g. 'Global Netmiko')."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    provider = models.ForeignKey(
        to=AutomationProvider,
        on_delete=models.PROTECT,
        related_name="configs",
    )
    parameters = models.JSONField(
        blank=True,
        null=True,
        help_text="Specific connection parameters (endpoints, options).",
    )
    secrets_group = models.ForeignKey(
        to=SecretsGroup,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    
    # Scoping
    scope_locations = models.ManyToManyField(
        to=Location,
        related_name="automation_provider_configs",
        blank=True,
    )
    scope_tenants = models.ManyToManyField(
        to=Tenant,
        related_name="automation_provider_configs",
        blank=True,
    )
    
    enabled = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.provider.name} - {self.name}"
