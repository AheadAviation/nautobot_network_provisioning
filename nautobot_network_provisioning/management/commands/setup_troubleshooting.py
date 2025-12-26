"""
Management command to set up the Troubleshooting Studio.

Usage:
    nautobot-server setup_troubleshooting
"""
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import Status


class Command(BaseCommand):
    help = 'Set up required Status objects for Troubleshooting Studio'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up Troubleshooting Studio...'))
        
        # Get the TroubleshootingRecord content type
        try:
            ct = ContentType.objects.get(
                app_label='nautobot_network_provisioning',
                model='troubleshootingrecord'
            )
        except ContentType.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    'TroubleshootingRecord model not found. '
                    'Please run migrations first: nautobot-server migrate'
                )
            )
            return
        
        # Create required statuses
        statuses = [
            ('pending', 'Pending', 'orange'),
            ('running', 'Running', 'blue'),
            ('completed', 'Completed', 'green'),
            ('failed', 'Failed', 'red'),
        ]
        
        created_count = 0
        updated_count = 0
        
        for slug, name, color in statuses:
            status, created = Status.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'color': color,
                }
            )
            
            # Add content type if not already added
            if ct not in status.content_types.all():
                status.content_types.add(ct)
                updated_count += 1
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created status: {name} ({slug})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  • Status already exists: {name} ({slug})')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Setup complete!'))
        self.stdout.write(f'  - Created {created_count} new status(es)')
        self.stdout.write(f'  - Updated {updated_count} existing status(es)')
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Install network-path-troubleshooting dependencies:')
        self.stdout.write('     pip install pyvis networkx napalm netmiko')
        self.stdout.write('  2. Copy network_path_tracing module to Python path')
        self.stdout.write('  3. Tag default gateways with network_gateway = True')
        self.stdout.write('  4. Create a SecretsGroup with Generic username/password')
        self.stdout.write('  5. Access the studio at:')
        self.stdout.write('     /plugins/network-provisioning/studio/tools/troubleshooting/')


