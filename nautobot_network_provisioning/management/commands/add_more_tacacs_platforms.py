"""
Management command to add Juniper, Palo Alto, and Fortinet strategies to TACACS+ task.
"""
from django.core.management.base import BaseCommand
from nautobot.dcim.models import Platform
from nautobot_network_provisioning.models import TaskIntent, TaskStrategy


class Command(BaseCommand):
    help = "Add Juniper JunOS, Palo Alto, and Fortinet strategies to existing TACACS+ task"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Adding more platform strategies to TACACS+ task..."))
        
        # Get the existing TACACS+ task
        try:
            task = TaskIntent.objects.get(slug="configure-tacacs")
            self.stdout.write(self.style.SUCCESS(f"✓ Found task: {task.name}"))
        except TaskIntent.DoesNotExist:
            self.stdout.write(self.style.ERROR("✗ TACACS+ task not found! Run create_tacacs_examples first."))
            return
        
        # Get or create platforms
        juniper, _ = Platform.objects.get_or_create(
            name="Juniper Junos",
            defaults={"description": "Juniper JunOS Network Operating System"}
        )
        
        palo_alto, _ = Platform.objects.get_or_create(
            name="Palo Alto PAN-OS",
            defaults={"description": "Palo Alto Networks PAN-OS"}
        )
        
        fortinet, _ = Platform.objects.get_or_create(
            name="Fortinet FortiOS",
            defaults={"description": "Fortinet FortiGate FortiOS"}
        )
        
        strategies_created = 0
        
        # =====================================================================
        # STRATEGY 5: Juniper JunOS
        # =====================================================================
        if not TaskStrategy.objects.filter(task_intent=task, platform=juniper).exists():
            TaskStrategy.objects.create(
                task_intent=task,
                platform=juniper,
                name="Juniper JunOS",
                method="cli_config",
                priority=100,
                template_content="""!
! TACACS+ Configuration for {{ device.name }}
! Platform: {{ device.platform.name }}
! Location: {{ device.location.name }}
! Generated: {{ now() }}
!
! ============================================================
! Juniper JunOS TACACS+ Configuration
! Uses set-based configuration commands
! ============================================================
!
configure
!
! Configure TACACS+ servers
{% for server in tacacs_servers %}
set system tacacs-server {{ server }} secret "{{ tacacs_key }}"
set system tacacs-server {{ server }} timeout {{ tacacs_timeout }}
set system tacacs-server {{ server }} single-connection
{% endfor %}
!
! Configure authentication order (TACACS+ first, then local)
set system authentication-order tacacs
set system authentication-order password
!
! Configure TACACS+ accounting
set system accounting events login
set system accounting events change-log
set system accounting events interactive-commands
set system accounting destination tacacs {
{% for server in tacacs_servers %}
    server {{ server }} {
        secret "{{ tacacs_key }}";
        timeout {{ tacacs_timeout }};
    }
{% endfor %}
}
!
! Configure authorization (TACACS+ for commands)
set system login user remote class super-user
!
! Configure privilege levels
set system login class tacacs-{{ enable_privilege_level }} permissions all
!
commit and-quit
"""
            )
            strategies_created += 1
            self.stdout.write(self.style.SUCCESS("  ✓ Strategy 5: Juniper JunOS (Priority: 100)"))
        else:
            self.stdout.write(self.style.WARNING("  ⚠ Juniper JunOS strategy already exists"))
        
        # =====================================================================
        # STRATEGY 6: Palo Alto PAN-OS
        # =====================================================================
        if not TaskStrategy.objects.filter(task_intent=task, platform=palo_alto).exists():
            TaskStrategy.objects.create(
                task_intent=task,
                platform=palo_alto,
                name="Palo Alto PAN-OS",
                method="cli_config",
                priority=100,
                template_content="""!
! TACACS+ Configuration for {{ device.name }}
! Platform: {{ device.platform.name }}
! Location: {{ device.location.name }}
! Generated: {{ now() }}
!
! ============================================================
! Palo Alto PAN-OS TACACS+ Configuration
! Uses set-based configuration with XML path structure
! ============================================================
!
configure
!
! Configure TACACS+ server profile
set shared server-profile tacacs TACACS_PROFILE
{% for server in tacacs_servers %}
set shared server-profile tacacs TACACS_PROFILE server TACACS_{{ loop.index }} address {{ server }}
set shared server-profile tacacs TACACS_PROFILE server TACACS_{{ loop.index }} secret {{ tacacs_key }}
set shared server-profile tacacs TACACS_PROFILE server TACACS_{{ loop.index }} timeout {{ tacacs_timeout }}
{% endfor %}
!
! Configure authentication profile
set shared authentication-profile TACACS_AUTH method tacacs-plus
set shared authentication-profile TACACS_AUTH tacacs-plus server-profile TACACS_PROFILE
!
! Configure authentication sequence (TACACS+ first, then local)
set deviceconfig system authentication-profile TACACS_AUTH
!
! Configure admin role with privilege level {{ enable_privilege_level }}
set shared admin-role tacacs-admin role superuser
!
! Configure authorization for TACACS+ users
set deviceconfig system tacacs-plus authorization enable yes
set deviceconfig system tacacs-plus authorization use-for-authentication yes
!
! Configure accounting
set deviceconfig system tacacs-plus accounting enable yes
set deviceconfig system tacacs-plus accounting server-profile TACACS_PROFILE
!
! Apply to management interface
set deviceconfig system type static
!
commit
exit
"""
            )
            strategies_created += 1
            self.stdout.write(self.style.SUCCESS("  ✓ Strategy 6: Palo Alto PAN-OS (Priority: 100)"))
        else:
            self.stdout.write(self.style.WARNING("  ⚠ Palo Alto PAN-OS strategy already exists"))
        
        # =====================================================================
        # STRATEGY 7: Fortinet FortiOS
        # =====================================================================
        if not TaskStrategy.objects.filter(task_intent=task, platform=fortinet).exists():
            TaskStrategy.objects.create(
                task_intent=task,
                platform=fortinet,
                name="Fortinet FortiOS",
                method="cli_config",
                priority=100,
                template_content="""!
! TACACS+ Configuration for {{ device.name }}
! Platform: {{ device.platform.name }}
! Location: {{ device.location.name }}
! Generated: {{ now() }}
!
! ============================================================
! Fortinet FortiGate TACACS+ Configuration
! Uses config-based CLI structure
! ============================================================
!
config system accprofile
    edit "tacacs-admin-profile"
        set secfabgrp read-write
        set ftviewgrp read-write
        set authgrp read-write
        set sysgrp read-write
        set netgrp read-write
        set loggrp read-write
        set fwgrp read-write
        set vpngrp read-write
        set utmgrp read-write
        set wanoptgrp read-write
        set wifi read-write
    next
end
!
! Configure TACACS+ servers
config system tacacs+
{% for server in tacacs_servers %}
    edit "TACACS_{{ loop.index }}"
        set server {{ server }}
        set key "{{ tacacs_key }}"
        set timeout {{ tacacs_timeout }}
        set authen-type auto
        set authorization enable
    next
{% endfor %}
end
!
! Configure admin user group for TACACS+
config system admin
    edit "tacacs-admin"
        set remote-auth enable
        set accprofile "tacacs-admin-profile"
        set vdom "root"
        set wildcard enable
        set remote-group "tacacs-users"
    next
end
!
! Configure authentication scheme (TACACS+ first, then local)
config system global
    set admin-server-cert enable
    set admintimeout {{ tacacs_timeout }}
end
!
! Configure user group for TACACS+ authentication
config user group
    edit "tacacs-users"
        set member "tacacs-admin"
        config match
            edit 1
                set server-name "TACACS_1"
                set group-name "network-admin"
            next
        end
    next
end
!
! Configure TACACS+ as primary authentication
config system global
    set remoteauthtimeout {{ tacacs_timeout }}
end
!
end
"""
            )
            strategies_created += 1
            self.stdout.write(self.style.SUCCESS("  ✓ Strategy 7: Fortinet FortiOS (Priority: 100)"))
        else:
            self.stdout.write(self.style.WARNING("  ⚠ Fortinet FortiOS strategy already exists"))
        
        # =====================================================================
        # Summary
        # =====================================================================
        total_strategies = task.strategies.count()
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("✓ PLATFORM STRATEGIES ADDED:"))
        self.stdout.write(self.style.SUCCESS(f"  Task: {task.name}"))
        self.stdout.write(self.style.SUCCESS(f"  New Strategies Added: {strategies_created}"))
        self.stdout.write(self.style.SUCCESS(f"  Total Strategies: {total_strategies}"))
        self.stdout.write(self.style.SUCCESS(""))
        self.stdout.write(self.style.SUCCESS("  Supported Platforms:"))
        for strategy in task.strategies.all().order_by('-priority', 'platform__name'):
            self.stdout.write(self.style.SUCCESS(f"    - {strategy.platform.name} ({strategy.get_method_display()}, Priority: {strategy.priority})"))
        self.stdout.write(self.style.SUCCESS("="*70))
        self.stdout.write(self.style.SUCCESS("\n✓ All platforms use the SAME 4 input variables:"))
        self.stdout.write(self.style.SUCCESS("  1. tacacs_servers (list[ip])"))
        self.stdout.write(self.style.SUCCESS("  2. tacacs_key (string)"))
        self.stdout.write(self.style.SUCCESS("  3. tacacs_timeout (integer)"))
        self.stdout.write(self.style.SUCCESS("  4. enable_privilege_level (integer)"))
        self.stdout.write(self.style.SUCCESS("\n✓ The system will automatically select the correct strategy"))
        self.stdout.write(self.style.SUCCESS("  based on the device's platform!"))

