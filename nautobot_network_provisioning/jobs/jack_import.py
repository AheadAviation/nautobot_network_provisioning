"""Jack Mapping Import job for bulk importing jack mappings from CSV."""

import csv
import io
from typing import Dict, List, Any

from django.db import transaction

from nautobot.apps.jobs import Job, FileVar, BooleanVar, register_jobs
from nautobot.dcim.models import Device, Interface, Location
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices

from nautobot_network_provisioning.models import JackMapping


class JackMappingImport(Job):
    """
    Bulk import jack mappings from CSV file.
    
    CSV Format:
    building,comm_room,jack,device_name,interface_name,description
    
    Example:
    Steacie,040,0228,switch-01,GigabitEthernet1/0/1,Floor 4 East
    """

    csv_file = FileVar(
        description="CSV file with jack mappings",
    )
    update_existing = BooleanVar(
        default=True,
        description="Update existing mappings if found",
    )
    dry_run = BooleanVar(
        default=False,
        description="Validate only, don't create/update records",
    )

    class Meta:
        name = "Jack Mapping Import"
        description = "Bulk import jack mappings from CSV file"
        has_sensitive_variables = False

    def run(self, csv_file, update_existing=True, dry_run=False):
        """Execute the jack mapping import."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            # Read CSV content
            try:
                content = csv_file.read().decode("utf-8")
            except UnicodeDecodeError:
                content = csv_file.read().decode("latin-1")
            
            # Parse CSV
            reader = csv.DictReader(io.StringIO(content))
            
            # Validate headers
            required_headers = {"building", "comm_room", "jack", "device_name", "interface_name"}
            if not required_headers.issubset(set(reader.fieldnames or [])):
                missing = required_headers - set(reader.fieldnames or [])
                self.logger.error(f"Missing required columns: {missing}")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log(f"Missing required columns: {missing}", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return f"Error: Missing required columns: {missing}"
            
            # Pre-load lookups
            buildings = {b.name.lower(): b for b in Location.objects.all()}
            devices = {d.name.lower(): d for d in Device.objects.all()}
            
            created = 0
            updated = 0
            errors = 0
            error_details = []
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
                try:
                    result = self._process_row(
                        row=row,
                        row_num=row_num,
                        buildings=buildings,
                        devices=devices,
                        update_existing=update_existing,
                        dry_run=dry_run,
                    )
                    
                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                    elif result == "skipped":
                        pass
                        
                except Exception as e:
                    errors += 1
                    error_msg = f"Row {row_num}: {str(e)}"
                    error_details.append(error_msg)
                    self.logger.error(error_msg)
            
            # Generate summary
            action = "Would have" if dry_run else ""
            summary_parts = []
            
            if created:
                summary_parts.append(f"{action} created {created}")
            if updated:
                summary_parts.append(f"{action} updated {updated}")
            if errors:
                summary_parts.append(f"{errors} errors")
            
            summary = ", ".join(summary_parts) if summary_parts else "No changes"
            
            if dry_run:
                summary = f"[DRY RUN] {summary}"
            
            self.logger.info(summary)
            
            # Log error details
            if error_details:
                self.logger.warning(f"Errors encountered:\n" + "\n".join(error_details[:20]))
                if len(error_details) > 20:
                    self.logger.warning(f"... and {len(error_details) - 20} more errors")
            
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

    @transaction.atomic
    def _process_row(
        self,
        row: Dict[str, str],
        row_num: int,
        buildings: Dict[str, Location],
        devices: Dict[str, Device],
        update_existing: bool,
        dry_run: bool,
    ) -> str:
        """Process a single CSV row."""
        # Extract fields
        building_name = row.get("building", "").strip()
        comm_room = row.get("comm_room", "").strip()
        jack = row.get("jack", "").strip()
        device_name = row.get("device_name", "").strip()
        interface_name = row.get("interface_name", "").strip()
        description = row.get("description", "").strip()
        
        # Validate required fields
        if not all([building_name, comm_room, jack, device_name, interface_name]):
            raise ValueError("Missing required field(s)")
        
        # Look up building
        building = buildings.get(building_name.lower())
        if not building:
            # Try partial match
            for name, loc in buildings.items():
                if building_name.lower() in name:
                    building = loc
                    break
        
        if not building:
            raise ValueError(f"Building not found: {building_name}")
        
        # Look up device
        device = devices.get(device_name.lower())
        if not device:
            raise ValueError(f"Device not found: {device_name}")
        
        # Look up interface
        interface = Interface.objects.filter(
            device=device,
            name=interface_name,
        ).first()
        
        if not interface:
            # Try partial match
            interface = Interface.objects.filter(
                device=device,
                name__icontains=interface_name,
            ).first()
        
        if not interface:
            raise ValueError(f"Interface not found: {device_name}/{interface_name}")
        
        # Check for existing mapping
        existing = JackMapping.objects.filter(
            building=building,
            comm_room__iexact=comm_room,
            jack__iexact=jack,
        ).first()
        
        if existing:
            if not update_existing:
                return "skipped"
            
            if not dry_run:
                existing.device = device
                existing.interface = interface
                existing.description = description
                existing.is_active = True
                existing.save()
            
            self.logger.info(f"Row {row_num}: Updated {building_name}/{comm_room}/{jack}")
            return "updated"
        else:
            if not dry_run:
                JackMapping.objects.create(
                    building=building,
                    comm_room=comm_room,
                    jack=jack,
                    device=device,
                    interface=interface,
                    description=description,
                    is_active=True,
                )
            
            self.logger.info(f"Row {row_num}: Created {building_name}/{comm_room}/{jack}")
            return "created"


register_jobs(JackMappingImport)
