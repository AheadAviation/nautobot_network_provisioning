"""MAC History Archiver job for cleaning up old MAC address history."""

from datetime import datetime, timedelta, timezone

from nautobot.apps.jobs import Job, IntegerVar, register_jobs
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices

from nautobot_network_provisioning.models import MACAddressHistory, ControlSetting


class MACHistoryArchiver(Job):
    """
    Archive (delete) MAC address history older than retention period.
    
    This job removes MAC address history records older than the configured
    retention period (default 30 days).
    """

    retention_days = IntegerVar(
        default=30,
        min_value=1,
        max_value=365,
        description="Delete history older than this many days",
    )

    class Meta:
        name = "MAC History Archiver"
        description = "Delete MAC address history older than retention period"
        has_sensitive_variables = False

    def run(self, retention_days=None):
        """Execute the history archival."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            # Get retention from control setting if not specified
            if retention_days is None:
                retention_str = ControlSetting.get_value("history_retention_days", "30")
                try:
                    retention_days = int(retention_str)
                except ValueError:
                    retention_days = 30
            
            self.logger.info(f"Archiving MAC history older than {retention_days} days")
            
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Count records to delete
            old_records = MACAddressHistory.objects.filter(last_seen__lt=cutoff_date)
            count = old_records.count()
            
            if count == 0:
                self.logger.info("No records to archive")
                self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
                self.job_result.log("No records to archive", level_choice=LogLevelChoices.LOG_INFO)
                self.job_result.save()
                return "No records to archive"
            
            self.logger.info(f"Found {count} records older than {cutoff_date}")
            
            # Delete in batches to avoid memory issues
            batch_size = 1000
            deleted_total = 0
            
            while True:
                # Get batch of IDs
                batch_ids = list(
                    MACAddressHistory.objects.filter(
                        last_seen__lt=cutoff_date
                    ).values_list("id", flat=True)[:batch_size]
                )
                
                if not batch_ids:
                    break
                
                # Delete batch
                deleted, _ = MACAddressHistory.objects.filter(id__in=batch_ids).delete()
                deleted_total += deleted
                
                self.logger.info(f"Deleted {deleted_total} of {count} records")
            
            summary = f"Archived {deleted_total} MAC history records older than {retention_days} days"
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


register_jobs(MACHistoryArchiver)
