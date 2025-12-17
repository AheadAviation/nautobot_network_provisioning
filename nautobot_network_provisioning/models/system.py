"""System models for NetAccess: ControlSetting."""

from django.db import models
from nautobot.core.models import BaseModel


# Default control settings matching TWIX controls
DEFAULT_CONTROL_SETTINGS = {
    "queue_processing_enabled": {
        "value": "true",
        "description": "Enable/disable the work queue processor job. When disabled, no port configuration changes will be applied.",
    },
    "write_mem_enabled": {
        "value": "true",
        "description": "Run 'write mem' (save config) after applying port configuration changes.",
    },
    "config_backup_enabled": {
        "value": "true",
        "description": "Backup interface configuration before making changes.",
    },
    "default_interface_enabled": {
        "value": "true",
        "description": "Default the interface before applying new configuration (clears existing config).",
    },
    "retry_failed_enabled": {
        "value": "false",
        "description": "Automatically retry failed queue entries on next processor run.",
    },
}


class ControlSetting(BaseModel):
    """
    System-wide control settings/toggles.
    
    This replaces the TWIX `controls` table. Common settings:
    - queue_processing_enabled: Enable/disable queue processing
    - write_mem_enabled: Save config after changes
    - config_backup_enabled: Backup config before changes
    - default_interface_enabled: Default interface before applying config
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Setting name (e.g., 'queue_processing_enabled')",
    )
    value = models.CharField(
        max_length=100,
        help_text="Setting value (true/false for boolean settings)",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this setting controls",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Control Setting"
        verbose_name_plural = "Control Settings"

    def __str__(self):
        return f"{self.name}: {self.value}"
    
    @property
    def is_boolean(self) -> bool:
        """Check if this is a boolean-style setting."""
        return self.value.lower() in (
            "true", "false", "yes", "no", "enable", "enabled", 
            "disable", "disabled", "on", "off", "1", "0"
        )
    
    @property
    def as_boolean(self) -> bool:
        """Get the value as a boolean."""
        return self.value.lower() in ("true", "yes", "enable", "enabled", "on", "1")

    @classmethod
    def is_enabled(cls, name: str, default: bool = False) -> bool:
        """
        Check if a control setting is enabled.
        
        Args:
            name: The setting name to check
            default: Default value if setting doesn't exist
            
        Returns:
            True if the setting value indicates enabled, False otherwise
        """
        try:
            setting = cls.objects.get(name=name)
            return setting.value.lower() in ("true", "yes", "enable", "enabled", "on", "1")
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_value(cls, name: str, default: str = "") -> str:
        """
        Get a control setting value.
        
        Args:
            name: The setting name to retrieve
            default: Default value if setting doesn't exist
            
        Returns:
            The setting value or default
        """
        try:
            setting = cls.objects.get(name=name)
            return setting.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, name: str, value: str, description: str = "") -> "ControlSetting":
        """
        Set a control setting value.
        
        Args:
            name: The setting name
            value: The value to set
            description: Optional description
            
        Returns:
            The created or updated ControlSetting instance
        """
        obj, _ = cls.objects.update_or_create(
            name=name,
            defaults={"value": value, "description": description}
        )
        return obj
    
    @classmethod
    def toggle(cls, name: str) -> bool:
        """
        Toggle a boolean control setting.
        
        Args:
            name: The setting name to toggle
            
        Returns:
            The new boolean value
            
        Raises:
            DoesNotExist: If the setting doesn't exist
        """
        setting = cls.objects.get(name=name)
        new_value = not setting.as_boolean
        setting.value = "true" if new_value else "false"
        setting.save()
        return new_value
    
    @classmethod
    def ensure_defaults(cls) -> int:
        """
        Ensure all default control settings exist.
        
        Creates any missing default settings. Does not modify existing settings.
        
        Returns:
            Number of settings created
        """
        created_count = 0
        for name, config in DEFAULT_CONTROL_SETTINGS.items():
            obj, created = cls.objects.get_or_create(
                name=name,
                defaults={
                    "value": config["value"],
                    "description": config["description"],
                }
            )
            if created:
                created_count += 1
        return created_count
