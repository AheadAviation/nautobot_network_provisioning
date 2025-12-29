from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.contrib.contenttypes.models import ContentType
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import Status, SecretsGroup
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from .models import TroubleshootingRecord
from .services.troubleshooting import (
    NetworkPathSettings,
    NautobotORMDataSource,
    InputValidationStep,
    GatewayDiscoveryStep,
    NextHopDiscoveryStep,
    PathTracingStep,
    build_pyvis_network,
)
import datetime
import json
import logging
from dataclasses import replace

# Check if all required modules are available
try:
    from .services.troubleshooting import resolve_target_to_ipv4
    NETWORK_PATH_TRACING_AVAILABLE = True
except ImportError:
    NETWORK_PATH_TRACING_AVAILABLE = False


@method_decorator(login_required, name='dispatch')
class StudioTroubleshootingLauncherView(View):
    """
    Real-time Network Path Troubleshooting Studio
    
    Uses the SPA Island pattern to provide a real-time, interactive troubleshooting
    interface with live updates as the trace progresses through the network.
    """
    template_name = "nautobot_network_provisioning/studio_tools/troubleshooting_studio.html"

    def get(self, request):
        """Render the Studio shell with API context."""
        secrets_groups = SecretsGroup.objects.all()
        
        # Get user permissions
        perms = {
            'add_troubleshootingrecord': request.user.has_perm('nautobot_network_provisioning.add_troubleshootingrecord'),
            'view_troubleshootingrecord': request.user.has_perm('nautobot_network_provisioning.view_troubleshootingrecord'),
        }
        
        context = {
            "secrets_groups": secrets_groups,
            "perms_json": json.dumps(perms),
            "network_path_tracing_available": NETWORK_PATH_TRACING_AVAILABLE,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        mode = request.POST.get("mode")

        if mode == "device":
            device_name = (request.POST.get("device_name") or "").strip()
            if not device_name:
                messages.error(request, "Device name is required.")
                return redirect(request.path)
            device = Device.objects.filter(name__iexact=device_name).first()
            if not device:
                messages.error(request, f"Device '{device_name}' not found.")
                return redirect(request.path)
            return redirect(
                "plugins:nautobot_network_provisioning:troubleshooting",
                model_label="dcim.device",
                pk=device.pk,
            )

        if mode == "interface":
            device_name = (request.POST.get("device_name") or "").strip()
            interface_name = (request.POST.get("interface_name") or "").strip()
            if not device_name or not interface_name:
                messages.error(request, "Device name and Interface name are required.")
                return redirect(request.path)
            device = Device.objects.filter(name__iexact=device_name).first()
            if not device:
                messages.error(request, f"Device '{device_name}' not found.")
                return redirect(request.path)
            interface = Interface.objects.filter(device=device, name__iexact=interface_name).first()
            if not interface:
                messages.error(request, f"Interface '{interface_name}' not found on '{device.name}'.")
                return redirect(request.path)
            return redirect(
                "plugins:nautobot_network_provisioning:troubleshooting",
                model_label="dcim.interface",
                pk=interface.pk,
            )

        messages.error(request, "Invalid selection.")
        return redirect(request.path)


class TroubleshootingView(View):
    """View for the Troubleshooting tab on Device/Interface."""
    template_name = "nautobot_network_provisioning/troubleshooting.html"

    def get(self, request, model_label, pk):
        app_label, model_name = model_label.split(".")
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        obj = get_object_or_404(ct.model_class(), pk=pk)
        
        records = TroubleshootingRecord.objects.filter(
            object_type=ct,
            object_id=obj.pk
        ).order_by("-start_time")
        
        secrets_groups = SecretsGroup.objects.all()
        
        # Determine default source IP
        source_ip = ""
        if isinstance(obj, Device) and obj.primary_ip:
            source_ip = str(obj.primary_ip.address).split("/")[0]
        elif isinstance(obj, Interface):
            # Try to find an IP on this interface
            ip = obj.ip_addresses.first()
            if ip:
                source_ip = str(ip.address).split("/")[0]

        return render(request, self.template_name, {
            "object": obj,
            "records": records,
            "secrets_groups": secrets_groups,
            "default_source_ip": source_ip,
            "model_label": model_label,
        })

    def post(self, request, model_label, pk):
        app_label, model_name = model_label.split(".")
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        obj = get_object_or_404(ct.model_class(), pk=pk)
        
        source_host = request.POST.get("source_host")
        destination_host = request.POST.get("destination_host")
        secrets_group_id = request.POST.get("secrets_group")
        
        if not source_host or not destination_host or not secrets_group_id:
            messages.error(request, "Source, Destination, and Secrets Group are required.")
            return redirect(request.path)

        secrets_group = get_object_or_404(SecretsGroup, pk=secrets_group_id)
        
        # Create record
        record = TroubleshootingRecord.objects.create(
            operation_type="path_trace",
            user=request.user,
            object_type=ct,
            object_id=obj.pk,
            status="pending",
            source_host=source_host,
            destination_host=destination_host,
        )
        
        # Execute trace (synchronously for now, should be async in production)
        self._run_trace(record, secrets_group)
        
        return redirect(request.path)

    def _run_trace(self, record, secrets_group):
        """Run the actual path trace logic."""
        record.status = "running"
        record.save()
        
        try:
            # 1. Get credentials from SecretsGroup
            username = secrets_group.get_secret_value(
                SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                SecretsGroupSecretTypeChoices.TYPE_USERNAME,
            )
            password = secrets_group.get_secret_value(
                SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
            )
            
            # 2. Setup settings
            base_settings = NetworkPathSettings(
                source_ip=record.source_host,
                destination_ip=record.destination_host,
            )
            settings = replace(
                base_settings,
                pa=replace(base_settings.pa, username=username, password=password),
                napalm=replace(base_settings.napalm, username=username, password=password),
                f5=replace(base_settings.f5, username=username, password=password),
            )
            
            # 3. Run steps
            data_source = NautobotORMDataSource()
            validation_step = InputValidationStep(data_source)
            gateway_step = GatewayDiscoveryStep(data_source, settings.gateway_custom_field)
            next_hop_step = NextHopDiscoveryStep(data_source, settings)
            path_tracing_step = PathTracingStep(data_source, settings, next_hop_step)
            
            validation = validation_step.run(settings)
            gateway = gateway_step.run(validation)
            path_result = path_tracing_step.run(validation, gateway)
            
            # 4. Generate visualization
            html = ""
            if path_result.graph:
                net = build_pyvis_network(path_result.graph)
                html = net.generate_html()
            
            # 5. Save results
            record.result_data = {
                "issues": path_result.issues,
                "paths_count": len(path_result.paths),
            }
            record.interactive_html = html
            record.status = "completed"
            record.end_time = datetime.datetime.now()
            record.save()
            
        except Exception as e:
            record.status = "failed"
            record.result_data = {"error": str(e)}
            record.end_time = datetime.datetime.now()
            record.save()


class TroubleshootingVisualView(View):
    """Serve the raw interactive HTML for the iframe."""
    def get(self, request, pk):
        record = get_object_or_404(TroubleshootingRecord, pk=pk)
        return HttpResponse(record.interactive_html)


@method_decorator(login_required, name='dispatch')
class TroubleshootingRunAPIView(View):
    """
    API endpoint to run a network path trace asynchronously.
    
    POST /plugins/network-provisioning/api/troubleshooting/run/
    {
        "source_ip": "10.0.0.1",
        "destination_ip": "8.8.8.8",
        "secrets_group_id": "uuid",
        "enable_layer2_discovery": true,
        "ping_endpoints": false
    }
    
    Returns:
    {
        "record_id": "uuid",
        "status": "running"
    }
    """
    
    def post(self, request):
        """Start a new path trace."""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        
        source_ip = data.get("source_ip")
        destination_ip = data.get("destination_ip")
        secrets_group_id = data.get("secrets_group_id")
        enable_layer2_discovery = data.get("enable_layer2_discovery", True)
        ping_endpoints = data.get("ping_endpoints", False)
        
        if not source_ip or not destination_ip or not secrets_group_id:
            return JsonResponse({
                "error": "source_ip, destination_ip, and secrets_group_id are required"
            }, status=400)
        
        try:
            secrets_group = SecretsGroup.objects.get(pk=secrets_group_id)
        except SecretsGroup.DoesNotExist:
            return JsonResponse({"error": "Secrets group not found"}, status=404)
        
        # Create record
        record = TroubleshootingRecord.objects.create(
            operation_type="path_trace",
            user=request.user,
            status="pending",
            source_host=source_ip,
            destination_host=destination_ip,
        )
        
        # Run trace asynchronously (for now, we'll run it synchronously)
        # In production, this should be a Celery task or similar
        self._run_trace_async(record, secrets_group, enable_layer2_discovery, ping_endpoints)
        
        return JsonResponse({
            "record_id": str(record.pk),
            "status": "running",
        })
    
    def _run_trace_async(self, record, secrets_group, enable_layer2_discovery, ping_endpoints):
        """Run the trace (should be async in production)."""
        import threading
        thread = threading.Thread(
            target=self._run_trace,
            args=(record, secrets_group, enable_layer2_discovery, ping_endpoints)
        )
        thread.daemon = True
        thread.start()
    
    def _run_trace(self, record, secrets_group, enable_layer2_discovery, ping_endpoints):
        """Run the actual path trace logic using the step-based API."""
        logger = logging.getLogger(__name__)
        
        record.status = "running"
        record.save()
        
        try:
            # Get credentials from SecretsGroup
            username = secrets_group.get_secret_value(
                SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                SecretsGroupSecretTypeChoices.TYPE_USERNAME,
            )
            password = secrets_group.get_secret_value(
                SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
            )
            
            # Setup settings
            base_settings = NetworkPathSettings(
                source_ip=record.source_host,
                destination_ip=record.destination_host,
            )
            settings = replace(
                base_settings,
                pa=replace(base_settings.pa, username=username, password=password),
                napalm=replace(base_settings.napalm, username=username, password=password),
                f5=replace(base_settings.f5, username=username, password=password),
                enable_layer2_discovery=enable_layer2_discovery,
            )
            
            # Run steps
            data_source = NautobotORMDataSource()
            validation_step = InputValidationStep(data_source)
            gateway_step = GatewayDiscoveryStep(data_source, settings.gateway_custom_field)
            next_hop_step = NextHopDiscoveryStep(data_source, settings, logger=logger)
            
            # Define hop callback for real-time updates
            def hop_callback(hop_data):
                """Update record with incremental hop data."""
                try:
                    # Refresh record from DB to avoid race conditions
                    record.refresh_from_db()
                    if record.hops_data is None:
                        record.hops_data = {"hops": []}
                    if "hops" not in record.hops_data:
                        record.hops_data["hops"] = []
                    record.hops_data["hops"].append(hop_data)
                    record.save(update_fields=["hops_data"])
                except Exception as e:
                    logger.warning(f"Failed to update hops_data: {e}")
            
            path_tracing_step = PathTracingStep(
                data_source, 
                settings, 
                next_hop_step, 
                logger=logger,
                hop_callback=hop_callback
            )
            
            # Initialize hops_data
            record.hops_data = {"hops": []}
            record.save(update_fields=["hops_data"])
            
            validation = validation_step.run(settings)
            gateway = gateway_step.run(validation)
            path_result = path_tracing_step.run(validation, gateway)
            
            # Build result data
            reached_destination = any(path.reached_destination for path in path_result.paths)
            result_data = {
                "status": "success" if reached_destination else "failed",
                "issues": path_result.issues,
                "paths_count": len(path_result.paths),
                "reached_destination": reached_destination,
                "paths": [
                    {
                        "path": index,
                        "hops": [
                            {
                                "device_name": hop.device_name,
                                "interface_name": hop.interface_name,
                                "egress_interface": hop.egress_interface,
                                "next_hop_ip": hop.next_hop_ip,
                                "details": hop.details,
                            }
                            for hop in path.hops
                        ],
                        "reached_destination": path.reached_destination,
                        "issues": path.issues,
                    }
                    for index, path in enumerate(path_result.paths, start=1)
                ],
            }
            
            # Generate visualization
            html = ""
            if path_result.graph:
                net = build_pyvis_network(path_result.graph)
                html = net.generate_html()
            
            # Save results
            record.result_data = result_data
            record.interactive_html = html
            record.status = "completed"
            record.end_time = datetime.datetime.now()
            record.save()
            
        except Exception as e:
            logger.exception("Path trace failed")
            record.status = "failed"
            record.result_data = {"error": str(e)}
            record.end_time = datetime.datetime.now()
            record.save()


@method_decorator(login_required, name='dispatch')
class TroubleshootingStatusAPIView(View):
    """
    API endpoint to check the status of a running trace.
    
    GET /plugins/network-provisioning/api/troubleshooting/status/<uuid>/
    
    Returns:
    {
        "record_id": "uuid",
        "status": "running|completed|failed",
        "result_data": {...},
        "start_time": "...",
        "end_time": "..."
    }
    """
    
    def get(self, request, pk):
        """Get trace status."""
        try:
            record = TroubleshootingRecord.objects.get(pk=pk)
        except TroubleshootingRecord.DoesNotExist:
            return JsonResponse({"error": "Record not found"}, status=404)
        
        return JsonResponse({
            "record_id": str(record.pk),
            "status": record.status.name if record.status else "unknown",
            "status_display": record.status.name if record.status else "Unknown",
            "result_data": record.result_data or {},
            "hops_data": record.hops_data or {},
            "source_host": record.source_host,
            "destination_host": record.destination_host,
            "start_time": record.start_time.isoformat() if record.start_time else None,
            "end_time": record.end_time.isoformat() if record.end_time else None,
            "has_visualization": bool(record.interactive_html),
        })


@method_decorator(login_required, name='dispatch')
class TroubleshootingHistoryAPIView(View):
    """
    API endpoint to get troubleshooting history.
    
    GET /plugins/network-provisioning/api/troubleshooting/history/
    
    Returns:
    {
        "records": [...]
    }
    """
    
    def get(self, request):
        """Get troubleshooting history."""
        records = TroubleshootingRecord.objects.filter(
            user=request.user
        ).order_by("-start_time")[:50]
        
        return JsonResponse({
            "records": [
                {
                    "id": str(record.pk),
                    "source_host": record.source_host,
                    "destination_host": record.destination_host,
                    "status": record.status.name if record.status else "unknown",
                    "status_display": record.status.name if record.status else "Unknown",
                    "start_time": record.start_time.isoformat() if record.start_time else None,
                    "end_time": record.end_time.isoformat() if record.end_time else None,
                }
                for record in records
            ]
        })
