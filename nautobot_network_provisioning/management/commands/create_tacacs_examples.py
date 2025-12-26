"""
Management command to create example TACACS+ configuration task with multiple strategies.
"""
from django.core.management.base import BaseCommand
from nautobot.dcim.models import Platform
from nautobot_network_provisioning.models import TaskIntent, TaskStrategy


class Command(BaseCommand):
    help = "Create TACACS+ task intent with strategies for different IOS versions and platforms"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Creating TACACS+ Task Intent with multiple strategies..."))
        
        # Get platforms
        cisco_ios = Platform.objects.filter(name__icontains="Cisco IOS").first()
        cisco_nxos = Platform.objects.filter(name__icontains="Cisco NXOS").first()
        arista_eos = Platform.objects.filter(name__icontains="Arista EOS").first()
        
        if not cisco_ios:
            self.stdout.write(self.style.ERROR("✗ Cisco IOS platform not found!"))
            return
        
        # =====================================================================
        # ONE TASK INTENT: Configure TACACS+
        # =====================================================================
        task, created = TaskIntent.objects.get_or_create(
            slug="configure-tacacs",
            defaults={
                "name": "Configure TACACS+ Authentication",
                "description": "Configure TACACS+ servers for device authentication and authorization. Supports multiple platforms and IOS versions.",
                "category": "security",
                "inputs": [
                    {
                        "name": "tacacs_servers",
                        "label": "TACACS+ Server IP Addresses",
                        "type": "list[ip]",
                        "source": "input",
                        "required": True,
                        "default": ["10.1.1.10", "10.1.1.11"],
                        "help_text": "List of TACACS+ server IP addresses in priority order"
                    },
                    {
                        "name": "tacacs_key",
                        "label": "TACACS+ Shared Secret",
                        "type": "string",
                        "source": "input",
                        "required": True,
                        "default": "MySecretKey123",
                        "help_text": "Shared secret for TACACS+ authentication (use vault in production!)"
                    },
                    {
                        "name": "tacacs_timeout",
                        "label": "TACACS+ Timeout (seconds)",
                        "type": "integer",
                        "source": "input",
                        "required": False,
                        "default": 5,
                        "help_text": "Timeout for TACACS+ server responses"
                    },
                    {
                        "name": "enable_privilege_level",
                        "label": "Enable Privilege Level",
                        "type": "integer",
                        "source": "input",
                        "required": False,
                        "default": 15,
                        "help_text": "Privilege level for enable mode (typically 15)"
                    }
                ]
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created Task Intent: {task.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Task Intent already exists: {task.name}"))
            # Delete existing strategies to recreate them
            deleted_count = task.strategies.all().delete()[0]
            if deleted_count > 0:
                self.stdout.write(self.style.WARNING(f"  Deleted {deleted_count} existing strategies"))
        
        strategies_created = 0
        
        # =====================================================================
        # STRATEGY 1: Cisco IOS 15+ (Modern Syntax) - HIGHEST PRIORITY
        # =====================================================================
        TaskStrategy.objects.create(
            task_intent=task,
            platform=cisco_ios,
            name="Cisco IOS 15+ (Modern Syntax)",
            method="cli_config",
            priority=100,  # Higher priority - preferred for IOS 15+
            template_content="""!
! TACACS+ Configuration for {{ device.name }}
! Platform: {{ device.platform.name }} - IOS 15+ Modern Syntax
! Location: {{ device.location.name }}
! Generated: {{ now() }}
!
! ============================================================
! Modern IOS 15+ syntax with named TACACS+ servers
! Use this for IOS versions 15.0 and above
! ============================================================
!
aaa new-model
!
! Define TACACS+ server group
aaa group server tacacs+ TACACS_SERVERS
{% for server in tacacs_servers %}
 server name TACACS_{{ loop.index }}
{% endfor %}
!
! Configure named TACACS+ servers
{% for server in tacacs_servers %}
tacacs server TACACS_{{ loop.index }}
 address ipv4 {{ server }}
 key {{ tacacs_key }}
 timeout {{ tacacs_timeout }}
{% endfor %}
!
! Configure AAA authentication
aaa authentication login default group TACACS_SERVERS local
aaa authentication enable default group TACACS_SERVERS enable
!
! Configure AAA authorization
aaa authorization exec default group TACACS_SERVERS local
aaa authorization commands {{ enable_privilege_level }} default group TACACS_SERVERS local
!
! Configure AAA accounting
aaa accounting exec default start-stop group TACACS_SERVERS
aaa accounting commands {{ enable_privilege_level }} default start-stop group TACACS_SERVERS
!
! Set privilege level
privilege exec level {{ enable_privilege_level }} configure terminal
!
end
"""
        )
        strategies_created += 1
        self.stdout.write(self.style.SUCCESS("  ✓ Strategy 1: Cisco IOS 15+ (Priority: 100)"))
        
        # =====================================================================
        # STRATEGY 2: Cisco IOS 12.x (Legacy Syntax) - LOWER PRIORITY
        # NOTE: Using 'jinja2' method to differentiate from IOS 15+ strategy
        # =====================================================================
        TaskStrategy.objects.create(
            task_intent=task,
            platform=cisco_ios,
            name="Cisco IOS 12.x (Legacy Syntax)",
            method="jinja2",  # Different method to avoid unique constraint
            priority=50,  # Lower priority - fallback for older IOS
            template_content="""!
! TACACS+ Configuration for {{ device.name }}
! Platform: {{ device.platform.name }} - IOS 12.x Legacy Syntax
! Location: {{ device.location.name }}
! Generated: {{ now() }}
!
! ============================================================
! Legacy IOS 12.x syntax with tacacs-server host
! Use this for IOS versions below 15.0
! ============================================================
!
aaa new-model
!
! Configure TACACS+ servers (legacy syntax)
{% for server in tacacs_servers %}
tacacs-server host {{ server }} key {{ tacacs_key }} timeout {{ tacacs_timeout }}
{% endfor %}
!
! Configure AAA authentication (legacy)
aaa authentication login default group tacacs+ local
aaa authentication enable default group tacacs+ enable
!
! Configure AAA authorization (legacy)
aaa authorization exec default group tacacs+ local
aaa authorization commands {{ enable_privilege_level }} default group tacacs+ local
!
! Configure AAA accounting (legacy)
aaa accounting exec default start-stop group tacacs+
aaa accounting commands {{ enable_privilege_level }} default start-stop group tacacs+
!
! Set privilege level
privilege exec level {{ enable_privilege_level }} configure terminal
!
end
"""
        )
        strategies_created += 1
        self.stdout.write(self.style.SUCCESS("  ✓ Strategy 2: Cisco IOS 12.x (Priority: 50)"))
        
        # =====================================================================
        # STRATEGY 3: Cisco NX-OS (if platform exists)
        # =====================================================================
        if cisco_nxos:
            TaskStrategy.objects.create(
                task_intent=task,
                platform=cisco_nxos,
                name="Cisco NX-OS",
                method="cli_config",
                priority=100,
                template_content="""!
! TACACS+ Configuration for {{ device.name }}
! Platform: {{ device.platform.name }}
! Location: {{ device.location.name }}
! Generated: {{ now() }}
!
! Enable TACACS+ feature
feature tacacs+
!
! Configure TACACS+ server group
aaa group server tacacs+ TACACS_SERVERS
{% for server in tacacs_servers %}
    server {{ server }}
{% endfor %}
    use-vrf management
!
! Configure TACACS+ servers
{% for server in tacacs_servers %}
tacacs-server host {{ server }} key 7 {{ tacacs_key }} timeout {{ tacacs_timeout }}
{% endfor %}
!
! Configure AAA authentication
aaa authentication login default group TACACS_SERVERS local
aaa authentication login console group TACACS_SERVERS local
!
! Configure AAA authorization
aaa authorization commands default group TACACS_SERVERS local
!
! Configure AAA accounting
aaa accounting default group TACACS_SERVERS
!
end
copy running-config startup-config
"""
            )
            strategies_created += 1
            self.stdout.write(self.style.SUCCESS("  ✓ Strategy 3: Cisco NX-OS (Priority: 100)"))
        
        # =====================================================================
        # STRATEGY 4: Arista EOS (if platform exists)
        # =====================================================================
        if arista_eos:
            TaskStrategy.objects.create(
                task_intent=task,
                platform=arista_eos,
                name="Arista EOS",
                method="cli_config",
                priority=100,
                template_content="""!
! TACACS+ Configuration for {{ device.name }}
! Platform: {{ device.platform.name }}
! Location: {{ device.location.name }}
! Generated: {{ now() }}
!
! Configure TACACS+ server group
aaa group server tacacs+ TACACS_SERVERS
{% for server in tacacs_servers %}
   server {{ server }}
{% endfor %}
!
! Configure TACACS+ servers
{% for server in tacacs_servers %}
tacacs-server host {{ server }} key 7 {{ tacacs_key }} timeout {{ tacacs_timeout }}
{% endfor %}
!
! Configure AAA authentication
aaa authentication login default group TACACS_SERVERS local
aaa authentication enable default group TACACS_SERVERS local
!
! Configure AAA authorization
aaa authorization exec default group TACACS_SERVERS local
aaa authorization commands all default group TACACS_SERVERS local
!
! Configure AAA accounting
aaa accounting exec default start-stop group TACACS_SERVERS
aaa accounting commands all default start-stop group TACACS_SERVERS
!
end
write memory
"""
            )
            strategies_created += 1
            self.stdout.write(self.style.SUCCESS("  ✓ Strategy 4: Arista EOS (Priority: 100)"))
        
        # =====================================================================
        # Summary
        # =====================================================================
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("✓ INTENT-BASED TASK CREATED:"))
        self.stdout.write(self.style.SUCCESS(f"  Task: {task.name}"))
        self.stdout.write(self.style.SUCCESS(f"  Slug: {task.slug}"))
        self.stdout.write(self.style.SUCCESS(f"  ID: {task.id}"))
        self.stdout.write(self.style.SUCCESS(f"  Strategies: {strategies_created}"))
        self.stdout.write(self.style.SUCCESS(""))
        self.stdout.write(self.style.SUCCESS("  The system will automatically select the best strategy based on:"))
        self.stdout.write(self.style.SUCCESS("  - Device platform (Cisco IOS, NX-OS, Arista EOS, etc.)"))
        self.stdout.write(self.style.SUCCESS("  - Strategy priority (higher = preferred)"))
        self.stdout.write(self.style.SUCCESS("  - IOS version (15+ gets modern syntax, <15 gets legacy)"))
        self.stdout.write(self.style.SUCCESS("="*70))
        self.stdout.write(self.style.SUCCESS("\nYou can now view this task in the Studio!"))
        self.stdout.write(self.style.SUCCESS("Add more strategies for other platforms as needed."))
