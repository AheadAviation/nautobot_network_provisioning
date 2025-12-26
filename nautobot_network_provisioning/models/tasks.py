"""
Task Models v2.0 - Recipe-Based Task Architecture

A Task is like a recipe:
- TaskIntent: What it does (the "what")
- TaskStrategy: How to do it for a specific platform (the "how")
"""
from django.db import models
from django.contrib.contenttypes.models import ContentType
from nautobot.core.models.generics import PrimaryModel, OrganizationalModel
from nautobot.dcim.models import Platform, Manufacturer


class TaskIntent(PrimaryModel):
    """
    The 'What' - defines an automation capability.
    
    Think of this as the recipe card that says "Configure NTP Servers"
    without specifying HOW to do it on each platform.
    
    Maps to a YAML file in task-library/ for Git storage.
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Human-readable task name (e.g., 'Configure NTP Servers')"
    )
    slug = models.SlugField(
        max_length=100, 
        unique=True,
        help_text="Machine-readable identifier (e.g., 'configure_ntp_servers')"
    )
    description = models.TextField(
        blank=True,
        help_text="What this task does and when to use it"
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Functional category for organization (e.g., 'Device Provisioning', 'VLAN & Switching')"
    )
    folder = models.ForeignKey(
        to='nautobot_network_provisioning.Folder',
        on_delete=models.SET_NULL,
        related_name='tasks',
        blank=True,
        null=True,
        help_text="Folder for organization in Catalog Explorer"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # THE CONTRACT: What inputs does this task need?
    # ═══════════════════════════════════════════════════════════════════
    inputs = models.JSONField(
        default=list,
        blank=True,
        help_text="""
List of input variable definitions. Each input is an object:
{
  "name": "ntp_servers",           # Variable name
  "label": "NTP Server Addresses", # Human-readable label
  "type": "list[ip]",              # Smart type: string, integer, boolean, ip, cidr, list[ip], device, interface, vlan_id
  "required": true,                # Is this required?
  "default": null,                 # Default value
  "source": "input",               # Where to get value: input, config_context, device_attribute, local_context
  "source_path": null,             # Path for config_context/device_attribute (e.g., "ntp.servers")
  "help": "Description",           # Help text for form
  "choices": null                  # For 'select' type: [{"value": "a", "label": "Option A"}]
}
"""
    )
    
    # Legacy field - kept for migration compatibility
    input_schema = models.JSONField(
        blank=True,
        null=True,
        help_text="[DEPRECATED] Use 'inputs' instead. JSON Schema for backwards compatibility."
    )
    
    # Legacy field - kept for migration compatibility  
    variable_mappings = models.JSONField(
        blank=True,
        null=True,
        help_text="[DEPRECATED] Use 'inputs' with source/source_path instead."
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # VALIDATION & ROLLBACK
    # ═══════════════════════════════════════════════════════════════════
    validation_config = models.JSONField(
        blank=True,
        null=True,
        help_text="""
Pre/post validation checks:
{
  "pre_checks": [{"name": "...", "type": "ping", "targets": "{{ ntp_servers }}"}],
  "post_checks": [{"name": "...", "type": "cli_parse", "command": "...", "expect_contains": "..."}]
}
"""
    )
    rollback_template = models.TextField(
        blank=True,
        help_text="Jinja2 template for rollback (undo) commands"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # GIT SYNC METADATA
    # ═══════════════════════════════════════════════════════════════════
    source_file = models.CharField(
        max_length=255,
        blank=True,
        help_text="Path to YAML source file in task-library/ (e.g., 'cisco/ios/configure-ntp.yaml')"
    )
    source_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 hash of source file for change detection"
    )
    last_synced = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When this task was last synced from YAML"
    )

    class Meta:
        ordering = ("category", "name")
        verbose_name = "Task Intent"
        verbose_name_plural = "Task Intents"

    def __str__(self):
        return self.name
    
    @property
    def input_count(self):
        """Number of defined inputs."""
        return len(self.inputs) if self.inputs else 0
    
    @property
    def strategy_count(self):
        """Number of implementation strategies."""
        return self.strategies.count()
    
    @property
    def enabled_strategies(self):
        """Strategies that are enabled."""
        return self.strategies.filter(enabled=True)
    
    def get_strategy_for_platform(self, platform):
        """
        Get the best matching strategy for a platform.
        Returns the highest priority enabled strategy for this platform.
        """
        return self.strategies.filter(
            platform=platform,
            enabled=True
        ).order_by('-priority').first()
    
    def to_yaml_dict(self):
        """
        Export this task to a dictionary suitable for YAML serialization.
        Used by the Git sync job.
        """
        return {
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'category': self.category,
            'inputs': self.inputs,
            'validation': self.validation_config,
            'rollback': {
                'template': self.rollback_template
            } if self.rollback_template else None,
            'strategies': [
                s.to_yaml_dict() for s in self.strategies.all()
            ]
        }


class TaskStrategy(PrimaryModel):
    """
    The 'How' - platform-specific implementation.
    
    Each strategy defines HOW to execute a TaskIntent on a specific platform
    using a specific method (CLI, REST API, NETCONF, etc.).
    
    Renamed from TaskImplementation to better reflect its purpose:
    - A TaskIntent can have multiple strategies
    - Strategies are selected based on platform + priority
    - Different methods can coexist (CLI fallback to API, etc.)
    """
    task_intent = models.ForeignKey(
        TaskIntent,
        on_delete=models.CASCADE,
        related_name="strategies"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Human-readable strategy name (e.g., 'Cisco IOS CLI')"
    )
    
    platform = models.ForeignKey(
        Platform,
        on_delete=models.PROTECT,
        related_name="task_strategies",
        help_text="Target network platform (from Nautobot DCIM)"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # HOW TO EXECUTE
    # ═══════════════════════════════════════════════════════════════════
    METHOD_CHOICES = [
        # CLI-based methods
        ("cli_config", "CLI Configuration (Netmiko/NAPALM)"),
        ("cli_show", "CLI Show Commands (Netmiko)"),
        
        # API-based methods
        ("rest_api", "REST API Call"),
        ("netconf", "NETCONF RPC"),
        ("gnmi", "gNMI Set/Get"),
        ("restconf", "RESTCONF"),
        
        # Nautobot integration
        ("graphql", "Nautobot GraphQL Mutation"),
        
        # Scripting
        ("python", "Python Script"),
        ("ansible", "Ansible Playbook"),
        ("nornir", "Nornir Task"),
        
        # Legacy
        ("jinja2", "Jinja2 Template (Legacy)"),
    ]
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default="cli_config",
        help_text="Execution method for this strategy"
    )
    
    # Priority for strategy selection (higher = preferred)
    priority = models.PositiveIntegerField(
        default=100,
        help_text="Higher priority strategies are selected first (1-1000)"
    )
    
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this strategy is active"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # THE IMPLEMENTATION
    # ═══════════════════════════════════════════════════════════════════
    template_content = models.TextField(
        blank=True,
        help_text="""
The actual implementation code/template.

For cli_config/cli_show: Jinja2 template that renders to CLI commands
For rest_api: Jinja2 template that renders to JSON payload
For python: Python code with access to context
For netconf: NETCONF XML template
For graphql: GraphQL mutation template
"""
    )
    
    # Extra configuration for non-template methods
    method_config = models.JSONField(
        blank=True,
        null=True,
        help_text="""
Method-specific configuration. Examples:

For rest_api:
{
  "endpoint": "/api/v1/config/ntp",
  "method": "POST",
  "headers": {"Content-Type": "application/json"},
  "auth_type": "bearer"
}

For python:
{
  "function_name": "configure_ntp",
  "timeout": 60
}

For ansible:
{
  "playbook": "playbooks/configure_ntp.yml",
  "extra_vars": {"some_var": "value"}
}
"""
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # INHERITANCE & REUSE
    # ═══════════════════════════════════════════════════════════════════
    inherit_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='inheritors',
        help_text="Inherit template_content from another strategy (for platform variants)"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # LEGACY COMPATIBILITY
    # ═══════════════════════════════════════════════════════════════════
    logic_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="[DEPRECATED] Use 'method' instead"
    )

    class Meta:
        ordering = ["-priority", "platform"]
        unique_together = [["task_intent", "platform", "method"]]
        verbose_name = "Task Strategy"
        verbose_name_plural = "Task Strategies"

    def __str__(self):
        return f"{self.task_intent.name} - {self.platform.name} ({self.get_method_display()})"
    
    @property
    def effective_template(self):
        """
        Get the effective template content, considering inheritance.
        """
        if self.template_content:
            return self.template_content
        elif self.inherit_from:
            return self.inherit_from.effective_template
        return ""
    
    def to_yaml_dict(self):
        """
        Export this strategy to a dictionary suitable for YAML serialization.
        """
        data = {
            'name': self.name,
            'platform': self.platform.slug if self.platform else None,
            'method': self.method,
            'priority': self.priority,
            'enabled': self.enabled,
        }
        
        if self.template_content:
            data['template'] = self.template_content
        
        if self.method_config:
            data['method_config'] = self.method_config
            
        if self.inherit_from:
            data['inherit_from'] = self.inherit_from.platform.slug if self.inherit_from.platform else None
            
        return data
