"""
Work Queue Processor job for processing pending port configuration changes.

This job processes entries from the WorkQueue and applies configuration
templates to device interfaces using the config_push service.
"""

from datetime import datetime, timezone, timedelta
import traceback

from django.db import transaction
from nautobot.apps.jobs import Job, register_jobs, IntegerVar, BooleanVar
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices

from nautobot_network_provisioning.models import WorkQueueEntry, ControlSetting
from nautobot_network_provisioning.services.template_renderer import render_template, build_context
from nautobot_network_provisioning.services.config_push import (
    push_interface_config,
    get_interface_running_config,
    test_device_connection,
)


class WorkQueueProcessor(Job):
    """
    Process pending work queue entries.
    
    This job processes all pending and optionally failed work queue entries
    that are scheduled for now or earlier. It applies configuration
    templates to device interfaces using Netmiko.
    
    Features:
    - Respects ControlSetting for queue_processing_enabled
    - Respects ControlSetting for write_mem_enabled
    - Respects ControlSetting for config_backup_enabled
    - Supports retry of failed entries
    - Logs all configuration changes
    - Stores previous/applied config for audit
    """

    class Meta:
        name = "Work Queue Processor"
        description = "Process pending port configuration changes from the work queue"
        has_sensitive_variables = False

    # Job variables
    retry_failed = BooleanVar(
        default=False,
        label="Retry Failed Entries",
        description="Include failed entries in processing (retry them)",
    )
    max_entries = IntegerVar(
        default=100,
        min_value=1,
        max_value=1000,
        label="Max Entries",
        description="Maximum number of entries to process in this run",
    )
    dry_run = BooleanVar(
        default=False,
        label="Dry Run",
        description="Preview changes without actually pushing configuration",
    )

    def run(self, retry_failed=False, max_entries=100, dry_run=False):
        """Execute the work queue processing."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            # Check if queue processing is enabled
            if not ControlSetting.is_enabled("queue_processing_enabled", default=True):
                self.logger.warning("Queue processing is disabled via ControlSetting")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("Queue processing is disabled", level_choice=LogLevelChoices.LOG_WARNING)
                self.job_result.save()
                return "Queue processing is disabled"
            
            # Get control settings
            write_mem_enabled = ControlSetting.is_enabled("write_mem_enabled", default=True)
            config_backup_enabled = ControlSetting.is_enabled("config_backup_enabled", default=True)
            
            if dry_run:
                self.logger.info("DRY RUN MODE - No changes will be made")
                write_mem_enabled = False
            
            # Build the query for entries to process
            now = datetime.now(timezone.utc)
            statuses = ["pending"]
            if retry_failed:
                statuses.append("failed")
            
            entries = WorkQueueEntry.objects.filter(
                status__in=statuses,
                scheduled_time__lte=now,
            ).select_related(
                "device",
                "interface",
                "service",
                "template",
                "building",
            ).order_by(
                "-status",  # Failed first (if retrying)
                "scheduled_time"  # Then oldest first
            )[:max_entries]
            
            entries_list = list(entries)
            total_count = len(entries_list)
            
            self.logger.info(f"Found {total_count} entries to process (max: {max_entries})")
            
            if not entries_list:
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("No entries to process", level_choice=LogLevelChoices.LOG_INFO)
                self.job_result.save()
                return "No entries to process"
            
            processed = 0
            succeeded = 0
            failed = 0
            skipped = 0
            
            for entry in entries_list:
                processed += 1
                
                # Log entry details
                self.logger.info(
                    f"[{processed}/{total_count}] Processing: "
                    f"{entry.device.name}:{entry.interface.name} - {entry.service.name} "
                    f"(Building: {entry.building.name if entry.building else 'N/A'}, "
                    f"Jack: {entry.jack or 'N/A'})"
                )
                
                # Validate entry has required fields
                if not entry.device or not entry.interface:
                    self.logger.error(f"Entry {entry.id} missing device or interface")
                    entry.status = WorkQueueEntry.StatusChoices.FAILED
                    entry.status_message = "Missing device or interface"
                    entry.save()
                    failed += 1
                    continue
                
                if not entry.template:
                    self.logger.error(f"Entry {entry.id} missing template")
                    entry.status = WorkQueueEntry.StatusChoices.FAILED
                    entry.status_message = "No template assigned"
                    entry.save()
                    failed += 1
                    continue
                
                # Update status to in_progress
                entry.status = WorkQueueEntry.StatusChoices.IN_PROGRESS
                entry.attempted_time = datetime.now(timezone.utc)
                entry.save()
                
                try:
                    # Build context for template rendering
                    context = build_context(
                        device=entry.device,
                        interface=entry.interface,
                        service=entry.service,
                        building=entry.building,
                        comm_room=entry.comm_room or "",
                        jack=entry.jack or "",
                        requested_by=entry.requested_by or "",
                        vlan=entry.vlan,
                        template_version=entry.template.version if entry.template else 1,
                        template_instance=entry.template.instance if entry.template else 1,
                    )
                    
                    # Render the template
                    rendered_config = render_template(
                        template_text=entry.template.template_text,
                        device=entry.device,
                        interface=entry.interface,
                        service=entry.service,
                        building=entry.building,
                        comm_room=entry.comm_room,
                        jack=entry.jack,
                        requested_by=entry.requested_by,
                        vlan=entry.vlan,
                        template_version=entry.template.version,
                        template_instance=entry.template.instance,
                    )
                    
                    if dry_run:
                        # Just log what would be done
                        self.logger.info(f"DRY RUN: Would apply config:\n{rendered_config}")
                        entry.status = WorkQueueEntry.StatusChoices.PENDING
                        entry.status_message = f"Dry run - config preview generated"
                        entry.applied_config = rendered_config
                        skipped += 1
                    else:
                        # Push the configuration
                        result = push_interface_config(
                            device=entry.device,
                            interface=entry.interface,
                            config_text=rendered_config,
                            default_interface=True,
                            write_mem=write_mem_enabled,
                            backup_config=config_backup_enabled,
                        )
                        
                        if result.success:
                            entry.status = WorkQueueEntry.StatusChoices.COMPLETED
                            entry.completed_time = datetime.now(timezone.utc)
                            entry.previous_config = result.previous_config
                            entry.applied_config = result.applied_config
                            entry.status_message = "Configuration applied successfully"
                            succeeded += 1
                            
                            self.logger.info(
                                f"SUCCESS: Config applied to {entry.device.name}:{entry.interface.name}"
                            )
                            
                            if result.backup_path:
                                self.logger.info(f"Backup saved to: {result.backup_path}")
                        else:
                            entry.status = WorkQueueEntry.StatusChoices.FAILED
                            entry.status_message = result.error_message[:500]  # Truncate if too long
                            entry.previous_config = result.previous_config
                            failed += 1
                            
                            self.logger.error(
                                f"FAILED: {entry.device.name}:{entry.interface.name}: "
                                f"{result.error_message}"
                            )
                    
                except Exception as e:
                    entry.status = WorkQueueEntry.StatusChoices.FAILED
                    entry.status_message = f"Error: {str(e)[:500]}"
                    failed += 1
                    
                    self.logger.error(
                        f"EXCEPTION processing entry {entry.id}: {e}"
                    )
                    self.logger.debug(traceback.format_exc())
                
                entry.save()
            
            # Build summary
            if dry_run:
                summary = f"DRY RUN: Previewed {processed} entries"
            else:
                summary = f"Processed {processed} entries: {succeeded} succeeded, {failed} failed"
                if skipped > 0:
                    summary += f", {skipped} skipped"
            
            self.logger.info(summary)
            
            # Mark job as SUCCESS
            self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
            self.job_result.log(summary, level_choice=LogLevelChoices.LOG_INFO)
            self.job_result.save()
            
            return summary

        except Exception as e:
            error_message = f"Job failed with error: {str(e)}"
            self.logger.error(error_message)
            self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
            self.job_result.log(error_message, level_choice=LogLevelChoices.LOG_ERROR)
            self.job_result.save()
            raise


class WorkQueueConnectionTest(Job):
    """
    Test connectivity to devices in the work queue.
    
    This job tests connectivity to all devices that have pending
    work queue entries, allowing operators to identify connectivity
    issues before processing.
    """
    
    class Meta:
        name = "Work Queue Connection Test"
        description = "Test connectivity to devices with pending work queue entries"
        has_sensitive_variables = False

    def run(self):
        """Test connections to devices with pending entries."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            # Get unique devices with pending entries
            pending_entries = WorkQueueEntry.objects.filter(
                status="pending"
            ).select_related("device").values_list("device", flat=True).distinct()
            
            from nautobot.dcim.models import Device
            devices = Device.objects.filter(id__in=pending_entries)
            
            self.logger.info(f"Testing connectivity to {devices.count()} devices")
            
            success_count = 0
            failed_count = 0
            results = []
            
            for device in devices:
                success, message = test_device_connection(device)
                
                if success:
                    success_count += 1
                    self.logger.info(f"OK: {device.name} - {message}")
                else:
                    failed_count += 1
                    self.logger.error(f"FAIL: {device.name} - {message}")
                
                results.append({
                    "device": device.name,
                    "success": success,
                    "message": message,
                })
            
            summary = f"Tested {len(results)} devices: {success_count} OK, {failed_count} failed"
            
            # Mark job as SUCCESS
            self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
            self.job_result.log(summary, level_choice=LogLevelChoices.LOG_INFO)
            self.job_result.save()
            
            return summary

        except Exception as e:
            error_message = f"Job failed with error: {str(e)}"
            self.logger.error(error_message)
            self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
            self.job_result.log(error_message, level_choice=LogLevelChoices.LOG_ERROR)
            self.job_result.save()
            raise


register_jobs(WorkQueueProcessor, WorkQueueConnectionTest)
