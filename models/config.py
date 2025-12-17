"""Configuration models for NetAccess: PortService, SwitchProfile, ConfigTemplate, ConfigTemplateHistory."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from nautobot.apps.models import PrimaryModel

from nautobot_network_provisioning.validators import validate_jinja2_syntax, format_validation_error_for_form


class PortService(PrimaryModel):
    """
    Automated Task - defines a configuration action/task type.
    
    Examples: "Enable VoIP Port", "Set Access VLAN", "Disable Port", "Configure Trunk"
    
    This model groups related configuration templates together.
    Each task can have multiple templates for different platforms/versions.
    
    Previously named "Port Service" - renamed to "Automated Task" for clarity.
    The model name remains PortService for database backward compatibility.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique name for this automated task",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this automated task does",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this task is available for selection",
    )

    natural_key_field_names = ["name"]

    class Meta:
        ordering = ["name"]
        verbose_name = "Automated Task"
        verbose_name_plural = "Automated Tasks"

    def __str__(self):
        return self.name
    
    @property
    def template_count(self):
        """Return the number of templates associated with this task."""
        return self.templates.count()
    
    @property
    def active_template_count(self):
        """Return the number of active templates."""
        return self.templates.filter(is_active=True).count()


# Backward compatibility alias
AutomatedTask = PortService


class SwitchProfile(PrimaryModel):
    """
    Defines a switch type + IOS version pattern for template matching.
    
    Example: WS-C3850 with IOS pattern "16.%" or "3.%(%)SE%"
    
    This replaces the TWIX `switch` table.
    """

    name = models.CharField(
        max_length=100,
        help_text="Descriptive name for this switch profile",
    )
    device_type_pattern = models.CharField(
        max_length=100,
        help_text="Device model pattern (SQL LIKE syntax). E.g., 'WS-C3850%'",
    )
    os_version_pattern = models.CharField(
        max_length=100,
        help_text="OS version pattern (SQL LIKE syntax). E.g., '15.2(%)E%'",
    )
    platform = models.ForeignKey(
        to="dcim.Platform",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="switch_profiles",
        help_text="Optional: restrict to specific Nautobot platform",
    )
    priority = models.IntegerField(
        default=100,
        help_text="Lower number = higher priority when multiple profiles match",
    )

    natural_key_field_names = ["name"]

    class Meta:
        ordering = ["priority", "name"]
        verbose_name = "Switch Profile"
        verbose_name_plural = "Switch Profiles"

    def __str__(self):
        return f"{self.name} ({self.device_type_pattern})"


class ConfigTemplate(PrimaryModel):
    """
    Configuration template for a PortService + Manufacturer/Platform/Version combination.
    
    Supports date-based versioning with automatic history tracking.
    Uses Jinja2 template syntax with validation on save.
    
    Templates are matched to devices by:
    1. Manufacturer + Platform + SoftwareVersion (most specific)
    2. Manufacturer + Platform (fallback if no version-specific template)
    """

    service = models.ForeignKey(
        to=PortService,
        on_delete=models.PROTECT,
        related_name="templates",
        help_text="The port service this template applies to",
    )
    
    # Legacy field - kept for backward compatibility during migration
    switch_profile = models.ForeignKey(
        to=SwitchProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="templates",
        help_text="(Legacy) The switch profile this template is designed for",
    )

    # New matching fields - link to Nautobot core DCIM models
    manufacturer = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="config_templates",
        help_text="Device manufacturer this template applies to",
    )
    platform = models.ForeignKey(
        to="dcim.Platform",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="config_templates",
        help_text="Platform/OS type this template is designed for",
    )
    # ManyToMany for software versions - allows selecting multiple versions
    # that share the same configuration template
    software_versions = models.ManyToManyField(
        to="dcim.SoftwareVersion",
        blank=True,
        related_name="config_templates",
        help_text="Software versions this template applies to (leave empty for all versions)",
    )
    
    # Keep the old field temporarily for migration, will be removed
    software_version = models.ForeignKey(
        to="dcim.SoftwareVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",  # No reverse relation for deprecated field
        help_text="(Deprecated) Use software_versions instead",
    )

    # Legacy versioning fields - kept for backward compatibility
    instance = models.IntegerField(
        null=True,
        blank=True,
        help_text="(Legacy) Groups related template versions together",
    )
    version = models.IntegerField(
        default=1,
        help_text="Version number for this template",
    )

    # New date-based versioning
    effective_date = models.DateField(
        default=timezone.now,
        help_text="Date when this template version becomes active",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is currently active and available for use",
    )
    superseded_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supersedes",
        help_text="Newer template that replaces this one",
    )

    # Template content - Jinja2 syntax
    template_text = models.TextField(
        help_text=(
            "Jinja2 template for CLI configuration. "
            "Variables: {{ interface }}, {{ device_name }}, {{ building }}, {{ vlan }}, etc. "
            "Also supports legacy TWIX style: __INTERFACE__, __SWITCH__, __BUILDING__, __VLAN__"
        ),
    )

    # Audit
    created_by = models.CharField(
        max_length=100,
        blank=True,
        help_text="Username who created this template version",
    )

    # Track if template has been validated
    is_validated = models.BooleanField(
        default=False,
        editable=False,
        help_text="Whether the template has passed Jinja2 syntax validation",
    )
    validation_message = models.TextField(
        blank=True,
        editable=False,
        help_text="Last validation result message",
    )

    natural_key_field_names = ["service", "manufacturer", "platform", "version"]

    class Meta:
        ordering = ["service", "manufacturer", "platform", "-effective_date", "-version"]
        verbose_name = "Config Template"
        verbose_name_plural = "Config Templates"

    def __str__(self):
        if self.manufacturer and self.platform:
            return f"{self.service.name} - {self.manufacturer.name}/{self.platform.name} v{self.version}"
        elif self.switch_profile:
            return f"{self.service.name} - {self.switch_profile.name} v{self.version}"
        return f"{self.service.name} v{self.version}"
    
    @property
    def display_name(self):
        """Return a display-friendly name for the template."""
        parts = [self.service.name]
        if self.manufacturer:
            parts.append(self.manufacturer.name)
        if self.platform:
            parts.append(self.platform.name)
        if self.software_version:
            parts.append(str(self.software_version))
        parts.append(f"v{self.version}")
        return " / ".join(parts)

    def clean(self):
        """
        Validate the template_text field as valid Jinja2 syntax.
        
        Raises ValidationError with detailed line/column info if invalid.
        """
        super().clean()
        
        if self.template_text:
            result = validate_jinja2_syntax(self.template_text)
            
            if not result.is_valid:
                error_message = format_validation_error_for_form(result)
                raise ValidationError({
                    "template_text": f"Invalid Jinja2 template:\n{error_message}"
                })
            
            # Store validation result
            self.is_validated = True
            self.validation_message = f"Valid {result.template_type} template"
        else:
            self.is_validated = False
            self.validation_message = ""

    def save(self, *args, **kwargs):
        """
        Override save to ensure validation runs and track history.
        """
        # Check if this is an update (has pk) and template_text changed
        is_update = self.pk is not None
        old_template_text = None
        
        if is_update:
            try:
                old_instance = ConfigTemplate.objects.get(pk=self.pk)
                old_template_text = old_instance.template_text
            except ConfigTemplate.DoesNotExist:
                pass
        
        # Run validation
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Create history entry if template_text changed
        if is_update and old_template_text and old_template_text != self.template_text:
            ConfigTemplateHistory.objects.create(
                template=self,
                template_text=old_template_text,
                changed_by=self.created_by or "system",
                change_reason="Template updated",
            )
        elif not is_update:
            # First save - create initial history entry
            ConfigTemplateHistory.objects.create(
                template=self,
                template_text=self.template_text,
                changed_by=self.created_by or "system",
                change_reason="Initial version",
            )

    def validate_template(self) -> dict:
        """
        Validate the template and return detailed results.
        
        Returns:
            dict with 'is_valid', 'errors', 'warnings', and 'template_type'
        """
        result = validate_jinja2_syntax(self.template_text)
        return {
            "is_valid": result.is_valid,
            "errors": [str(e) for e in result.errors],
            "warnings": result.warnings,
            "template_type": result.template_type,
            "error_summary": result.error_summary,
        }

    def render_preview(self, context: dict = None) -> str:
        """
        Render the template with test/preview data.
        
        Args:
            context: Optional context dict for rendering
            
        Returns:
            Rendered template string
        """
        from nautobot_network_provisioning.services.template_renderer import render_template_from_context
        
        if context is None:
            # Use preview context
            context = {
                "interface": "GigabitEthernet1/0/1",
                "interface_name": "GigabitEthernet1/0/1",
                "device": None,
                "device_name": "demo-switch-01",
                "device_ip": "10.10.10.1",
                "building": None,
                "building_name": "Main Building",
                "comm_room": "MDF-1",
                "jack": "A-101",
                "vlan": 100,
                "service": self.service,
                "service_name": self.service.name if self.service else "DataPort",
                "requested_by": "admin",
                "creator": "admin",
                "template_version": self.version,
                "template_instance": self.instance,
            }
        
        return render_template_from_context(self.template_text, context)


class ConfigTemplateHistory(models.Model):
    """
    Automatic history tracking for ConfigTemplate changes.
    
    Each time a template is saved, a history entry is created to track
    the previous version. This enables viewing and reverting to past versions.
    """

    template = models.ForeignKey(
        to=ConfigTemplate,
        on_delete=models.CASCADE,
        related_name="history",
        help_text="The template this history entry belongs to",
    )
    template_text = models.TextField(
        help_text="Snapshot of the template content at this point in time",
    )
    changed_by = models.CharField(
        max_length=100,
        help_text="Username who made this change",
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this change was made",
    )
    change_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional description of why the change was made",
    )

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Config Template History"
        verbose_name_plural = "Config Template History"

    def __str__(self):
        return f"{self.template} @ {self.changed_at.strftime('%Y-%m-%d %H:%M')}"

    def restore(self):
        """
        Restore the template to this historical version.
        
        Returns:
            The updated ConfigTemplate instance
        """
        self.template.template_text = self.template_text
        self.template.save()
        return self.template
