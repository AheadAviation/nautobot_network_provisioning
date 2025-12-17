"""
Work Queue Bulk Import Job.

This job allows bulk importing work queue entries from a CSV file,
similar to the original TWIX upload.py functionality.

CSV Format:
    Building,CommRoom,Jack,ServiceName,VLAN,ScheduledDate
    
Example:
    Curtis Lecture Hall,MDF-1,A-101,Access-VoIP,290,2024-01-15 09:00
    Vari Hall,IDF-2,B-201,Access-Data,100,
    Ross Building,MDF-1,C-301,Unused-Port,,
    
Notes:
- ScheduledDate is optional; if empty, defaults to now (immediate processing)
- VLAN is optional; if empty, uses template default
- Building can be the full name or a partial match
- ServiceName must match an existing PortService name exactly
"""

import csv
from datetime import datetime
from io import StringIO

from django.utils import timezone
from nautobot.apps.jobs import Job, FileVar, BooleanVar, register_jobs
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices


class WorkQueueBulkImport(Job):
    """
    Import work queue entries from a CSV file.
    
    This replicates the TWIX upload.py functionality for bulk port configuration
    scheduling. Each row in the CSV creates a WorkQueueEntry that will be
    processed by the WorkQueueProcessor job.
    """

    class Meta:
        name = "Work Queue CSV Import"
        description = "Bulk import work queue entries from a CSV file"
        commit_default = False
        has_sensitive_variables = False

    csv_file = FileVar(
        description="CSV file with columns: Building,CommRoom,Jack,ServiceName,VLAN,ScheduledDate"
    )
    
    validate_only = BooleanVar(
        description="Validate CSV without creating entries (dry run)",
        default=True,
    )
    
    update_existing = BooleanVar(
        description="Update existing pending entries instead of skipping",
        default=False,
    )
    
    default_service = BooleanVar(
        description="Use 'Access-Data' as default if ServiceName not found",
        default=False,
    )

    def run(self, **kwargs):
        """Execute the work queue import job."""
        # Mark job as STARTED
        self.job_result.set_status(JobResultStatusChoices.STATUS_STARTED)
        self.job_result.log("Job execution has begun.", level_choice=LogLevelChoices.LOG_INFO)
        self.job_result.save()

        try:
            from nautobot_network_provisioning.models import (
                PortService,
                WorkQueueEntry,
                JackMapping,
                ConfigTemplate,
            )
            from nautobot_network_provisioning.services.jack_lookup import find_interface_unified
            from nautobot_network_provisioning.services.template_matcher import find_template_for_device
            
            csv_file = kwargs.get("csv_file")
            validate_only = kwargs.get("validate_only", True)
            update_existing = kwargs.get("update_existing", False)
            use_default_service = kwargs.get("default_service", False)
            
            if not csv_file:
                self.logger.error("No CSV file provided")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log("No CSV file provided", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return
            
            # Read CSV content
            try:
                content = csv_file.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8-sig")  # Handle BOM
            except Exception as e:
                self.logger.error(f"Failed to read CSV file: {e}")
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log(f"Failed to read CSV file: {e}", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return
            
            # Parse CSV
            reader = csv.DictReader(StringIO(content))
            
            # Map headers (handle variations)
            header_map = {}
            for h in reader.fieldnames or []:
                h_normalized = h.lower().replace(" ", "").replace("_", "")
                if "building" in h_normalized:
                    header_map["building"] = h
                elif "comm" in h_normalized and "room" in h_normalized:
                    header_map["comm_room"] = h
                elif "jack" in h_normalized or "port" in h_normalized:
                    header_map["jack"] = h
                elif "service" in h_normalized:
                    header_map["service"] = h
                elif "vlan" in h_normalized:
                    header_map["vlan"] = h
                elif "date" in h_normalized or "schedule" in h_normalized:
                    header_map["scheduled_date"] = h
                elif "user" in h_normalized or "request" in h_normalized:
                    header_map["requested_by"] = h
            
            # Check required headers
            missing = []
            for req in ["building", "comm_room", "jack", "service"]:
                if req not in header_map:
                    missing.append(req)
            
            if missing:
                self.logger.error(
                    f"Missing required columns: {', '.join(missing)}. "
                    f"Found columns: {', '.join(reader.fieldnames or [])}"
                )
                self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
                self.job_result.log(f"Missing required columns: {missing}", level_choice=LogLevelChoices.LOG_ERROR)
                self.job_result.save()
                return
            
            # Reset reader
            reader = csv.DictReader(StringIO(content))
            
            stats = {
                "total": 0,
                "valid": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
            }
            
            self.logger.info("=" * 60)
            self.logger.info("Work Queue CSV Import")
            self.logger.info("=" * 60)
            if validate_only:
                self.logger.warning("VALIDATION ONLY - No entries will be created")
            self.logger.info("")
            
            entries_to_create = []
            
            for row_num, row in enumerate(reader, start=2):
                stats["total"] += 1
                
                # Extract values
                building_name = row.get(header_map["building"], "").strip()
                comm_room = row.get(header_map["comm_room"], "").strip()
                jack = row.get(header_map["jack"], "").strip()
                service_name = row.get(header_map["service"], "").strip()
                vlan = row.get(header_map.get("vlan", ""), "").strip() if "vlan" in header_map else ""
                scheduled_date_str = row.get(header_map.get("scheduled_date", ""), "").strip() if "scheduled_date" in header_map else ""
                requested_by = row.get(header_map.get("requested_by", ""), "").strip() if "requested_by" in header_map else "csv_import"
                
                # Validate required fields
                if not all([building_name, comm_room, jack, service_name]):
                    self.logger.warning(
                        f"Row {row_num}: Missing required field(s) - "
                        f"building='{building_name}', comm_room='{comm_room}', "
                        f"jack='{jack}', service='{service_name}'"
                    )
                    stats["errors"] += 1
                    continue
                
                # Find service
                service = PortService.objects.filter(name=service_name, is_active=True).first()
                if not service:
                    if use_default_service:
                        service = PortService.objects.filter(name="Access-Data", is_active=True).first()
                        if service:
                            self.logger.warning(
                                f"Row {row_num}: Service '{service_name}' not found, using 'Access-Data'"
                            )
                        else:
                            self.logger.error(f"Row {row_num}: Service '{service_name}' not found and no default available")
                            stats["errors"] += 1
                            continue
                    else:
                        self.logger.error(f"Row {row_num}: Service '{service_name}' not found")
                        stats["errors"] += 1
                        continue
                
                # Find interface using unified lookup
                lookup_results = find_interface_unified(building_name, comm_room, jack)
                
                if not lookup_results:
                    self.logger.warning(
                        f"Row {row_num}: No interface found for {building_name}/{comm_room}/{jack}"
                    )
                    stats["errors"] += 1
                    continue
                
                # Use first result
                result = lookup_results[0]
                interface = result.get("interface")
                device = result.get("device")
                building = result.get("building")
                
                if not interface or not device:
                    self.logger.warning(
                        f"Row {row_num}: Could not resolve interface/device for {building_name}/{comm_room}/{jack}"
                    )
                    stats["errors"] += 1
                    continue
                
                # Find template
                template = find_template_for_device(device, service)
                if not template:
                    self.logger.warning(
                        f"Row {row_num}: No template found for device '{device.name}' and service '{service.name}'"
                    )
                    stats["errors"] += 1
                    continue
                
                # Parse scheduled date
                scheduled_time = timezone.now()
                if scheduled_date_str:
                    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d"]:
                        try:
                            scheduled_time = timezone.make_aware(
                                datetime.strptime(scheduled_date_str, fmt)
                            )
                            break
                        except ValueError:
                            continue
                    else:
                        self.logger.warning(
                            f"Row {row_num}: Could not parse date '{scheduled_date_str}', using now"
                        )
                
                # Parse VLAN
                vlan_int = None
                if vlan:
                    try:
                        vlan_int = int(vlan)
                    except ValueError:
                        self.logger.warning(f"Row {row_num}: Invalid VLAN '{vlan}', ignoring")
                
                # Check for existing pending entry
                existing = WorkQueueEntry.objects.filter(
                    device=device,
                    interface=interface,
                    status="pending",
                ).first()
                
                if existing:
                    if update_existing:
                        self.logger.info(
                            f"Row {row_num}: Will update existing entry for {device.name}/{interface.name}"
                        )
                    else:
                        self.logger.info(
                            f"Row {row_num}: Skipping - pending entry already exists for {device.name}/{interface.name}"
                        )
                        stats["skipped"] += 1
                        continue
                
                stats["valid"] += 1
                self.logger.info(
                    f"Row {row_num}: {building_name}/{comm_room}/{jack} -> "
                    f"{device.name}/{interface.name} ({service.name})"
                )
                
                # Prepare entry data
                entry_data = {
                    "device": device,
                    "interface": interface,
                    "building": building,
                    "comm_room": comm_room,
                    "jack": jack,
                    "service": service,
                    "template": template,
                    "vlan": vlan_int,
                    "scheduled_time": scheduled_time,
                    "status": "pending",
                    "requested_by": requested_by or "csv_import",
                }
                
                if existing and update_existing:
                    entries_to_create.append(("update", existing, entry_data))
                else:
                    entries_to_create.append(("create", None, entry_data))
            
            # Create/update entries if not validate-only
            if not validate_only and entries_to_create:
                self.logger.info("")
                self.logger.info("Creating/updating work queue entries...")
                
                for action, existing, data in entries_to_create:
                    try:
                        if action == "update" and existing:
                            for key, value in data.items():
                                setattr(existing, key, value)
                            existing.save()
                            stats["updated"] += 1
                            self.logger.info(
                                f"  Updated: {data['device'].name}/{data['interface'].name}"
                            )
                        else:
                            WorkQueueEntry.objects.create(**data)
                            stats["created"] += 1
                            self.logger.info(
                                f"  Created: {data['device'].name}/{data['interface'].name}"
                            )
                    except Exception as e:
                        self.logger.error(f"  Failed: {e}")
                        stats["errors"] += 1
            
            # Summary
            self.logger.info("")
            self.logger.info("=" * 60)
            self.logger.info("Import Summary")
            self.logger.info("=" * 60)
            self.logger.info(f"  Total rows processed:  {stats['total']}")
            self.logger.info(f"  Valid entries:         {stats['valid']}")
            if not validate_only:
                self.logger.info(f"  Created:               {stats['created']}")
                self.logger.info(f"  Updated:               {stats['updated']}")
            self.logger.info(f"  Skipped (existing):    {stats['skipped']}")
            self.logger.info(f"  Errors:                {stats['errors']}")
            
            if validate_only:
                self.logger.warning("")
                self.logger.warning("This was a validation run. No entries were created.")
                self.logger.warning("Uncheck 'Validate Only' to actually create entries.")
            
            # Mark job as SUCCESS
            summary = f"Processed {stats['total']} rows: {stats['valid']} valid, {stats['created']} created, {stats['errors']} errors"
            self.job_result.set_status(JobResultStatusChoices.STATUS_SUCCESS)
            self.job_result.log(summary, level_choice=LogLevelChoices.LOG_INFO)
            self.job_result.save()

        except Exception as e:
            error_message = f"Job failed with error: {str(e)}"
            self.logger.error(error_message)
            self.job_result.set_status(JobResultStatusChoices.STATUS_FAILURE)
            self.job_result.log(error_message, level_choice=LogLevelChoices.LOG_ERROR)
            self.job_result.save()
            raise


# Register the job
register_jobs(WorkQueueBulkImport)
