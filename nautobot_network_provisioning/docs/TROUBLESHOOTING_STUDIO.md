# Network Path Troubleshooting Studio

## Overview

The Network Path Troubleshooting Studio is a real-time, interactive tool for tracing network paths between IP endpoints. It integrates the standalone `network-path-troubleshooting` job into the Nautobot Network Provisioning app with a modern, SPA-style interface.

## Features

- **Real-time Path Tracing**: Watch as the trace progresses through your network hop-by-hop
- **Interactive Visualization**: PyVis-powered network graph showing the complete path
- **Live Logging**: See detailed logs as the trace executes
- **Trace History**: Access previous traces with one click
- **Multi-Platform Support**: Works with CLI (Netmiko, NAPALM), REST APIs, controllers, and more
- **Layer 2 Discovery**: Optional LLDP/ARP-based layer 2 neighbor discovery
- **ECMP Support**: Visualizes multiple paths when ECMP is in use

## Architecture

The Troubleshooting Studio uses the **SPA Island Pattern**:

1. **Django Shell** (`troubleshooting_studio.html`): Provides authentication and mounting point
2. **JavaScript Application** (`troubleshooting_studio.js`): Handles all UI rendering and state
3. **CSS Layout** (`troubleshooting_studio.css`): Full-screen grid layout with 2 zones
4. **REST API Endpoints**: Backend communication for trace execution and status

### Layout Zones

- **Zone A (Left Panel)**: Input form and trace history
- **Zone B (Main Stage)**: Real-time visualization and live logs

## Installation

### Prerequisites

1. **Nautobot Network Provisioning App** installed and configured
2. **Network Path Tracing Module** from the standalone job:
   ```bash
   # Install the network-path-troubleshooting dependencies
   pip install pyvis networkx napalm netmiko
   ```

3. **Custom Fields** (required):
   - `network_gateway` (Boolean on `ipam.IPAddress`): Marks default gateways
   
4. **Status Objects** (required for TroubleshootingRecord):
   - Create statuses: `pending`, `running`, `completed`, `failed`
   - Assign to content type: `nautobot_network_provisioning.troubleshootingrecord`

5. **Secrets Groups**: At least one SecretsGroup with Generic username/password

### Setup Steps

#### 1. Copy the Network Path Tracing Module

Copy the `network_path_tracing` module from your standalone job into your Python path:

```bash
# Option A: Copy to site-packages
cp -r /path/to/ansible-nautobot-network-path-troubleshooting/jobs/network_path_tracing \
      /path/to/site-packages/

# Option B: Add to PYTHONPATH
export PYTHONPATH="/path/to/ansible-nautobot-network-path-troubleshooting/jobs:$PYTHONPATH"
```

#### 2. Run Migrations

```bash
nautobot-server migrate nautobot_network_provisioning
```

This creates the `TroubleshootingRecord` model.

#### 3. Create Status Objects

```python
# In Nautobot shell (nautobot-server nbshell)
from nautobot.extras.models import Status
from django.contrib.contenttypes.models import ContentType

ct = ContentType.objects.get(app_label='nautobot_network_provisioning', model='troubleshootingrecord')

for slug, name, color in [
    ('pending', 'Pending', 'orange'),
    ('running', 'Running', 'blue'),
    ('completed', 'Completed', 'green'),
    ('failed', 'Failed', 'red'),
]:
    status, created = Status.objects.get_or_create(
        slug=slug,
        defaults={'name': name, 'color': color}
    )
    status.content_types.add(ct)
    print(f"{'Created' if created else 'Updated'} status: {name}")
```

#### 4. Tag Default Gateways

For each prefix in your network, tag the default gateway IP with `network_gateway = True`:

```python
# Example
from nautobot.ipam.models import IPAddress

gateway = IPAddress.objects.get(address='10.0.0.1/24')
gateway.cf['network_gateway'] = True
gateway.save()
```

#### 5. Access the Studio

Navigate to: `http://your-nautobot/plugins/network-provisioning/studio/tools/troubleshooting/`

## Usage

### Running a Trace

1. **Enter Source IP/FQDN**: The starting point (e.g., `10.0.0.10` or `server01.example.com`)
2. **Enter Destination IP/FQDN**: The target (e.g., `8.8.8.8` or `google.com`)
3. **Select Secrets Group**: Credentials for device access
4. **Configure Options**:
   - **Enable Layer 2 Discovery**: Include LLDP/ARP neighbor discovery
   - **Ping Endpoints First**: Refresh ARP/ND caches before tracing
5. **Click "Run Trace"**

### Viewing Results

- **Live Logs**: Watch the trace progress in the bottom log panel
- **Visualization**: Interactive network graph appears on completion
- **History**: Click any previous trace to reload its visualization

### Understanding the Visualization

- **Blue Nodes**: Source endpoint
- **Green Nodes**: Destination endpoint
- **Gray Nodes**: Intermediate hops (routers, firewalls, load balancers)
- **Red Nodes**: Error states (device unreachable, route not found)
- **Solid Lines**: Layer 3 hops
- **Dashed Lines**: Layer 2 connections
- **Hover**: See detailed information about each node and edge

## API Endpoints

The Troubleshooting Studio exposes REST API endpoints for programmatic access:

### Run a Trace

```http
POST /plugins/network-provisioning/api/troubleshooting/run/
Content-Type: application/json

{
  "source_ip": "10.0.0.1",
  "destination_ip": "8.8.8.8",
  "secrets_group_id": "uuid",
  "enable_layer2_discovery": true,
  "ping_endpoints": false
}
```

**Response:**
```json
{
  "record_id": "uuid",
  "status": "running"
}
```

### Check Status

```http
GET /plugins/network-provisioning/api/troubleshooting/status/<uuid>/
```

**Response:**
```json
{
  "record_id": "uuid",
  "status": "completed",
  "status_display": "Completed",
  "result_data": {...},
  "source_host": "10.0.0.1",
  "destination_host": "8.8.8.8",
  "start_time": "2025-12-26T10:00:00Z",
  "end_time": "2025-12-26T10:00:15Z",
  "has_visualization": true
}
```

### Get History

```http
GET /plugins/network-provisioning/api/troubleshooting/history/
```

**Response:**
```json
{
  "records": [
    {
      "id": "uuid",
      "source_host": "10.0.0.1",
      "destination_host": "8.8.8.8",
      "status": "completed",
      "status_display": "Completed",
      "start_time": "2025-12-26T10:00:00Z",
      "end_time": "2025-12-26T10:00:15Z"
    }
  ]
}
```

## Troubleshooting

### "Network path tracing module is not available"

**Cause**: The `network_path_tracing` module is not in your Python path.

**Solution**:
1. Verify the module is installed: `python -c "import network_path_tracing"`
2. Add to PYTHONPATH or copy to site-packages (see Installation)
3. Restart Nautobot services

### "Secrets group not found" or credential errors

**Cause**: SecretsGroup doesn't have Generic username/password defined.

**Solution**:
1. Go to Secrets → Secrets Groups
2. Edit your group and add:
   - Generic / Username
   - Generic / Password
3. Ensure the credentials have read access to your devices

### "No default gateway found"

**Cause**: The source IP's prefix doesn't have a gateway tagged with `network_gateway = True`.

**Solution**:
1. Find the prefix containing the source IP
2. Identify the default gateway IP in that prefix
3. Set `network_gateway = True` on that IPAddress object

### Trace hangs or times out

**Cause**: Device unreachable, authentication failure, or network issue.

**Solution**:
1. Check the live logs for specific error messages
2. Verify device primary IPs are correct in Nautobot
3. Test SSH/HTTPS connectivity manually
4. Verify credentials in SecretsGroup
5. Check firewall rules between Nautobot and devices

### Visualization doesn't load

**Cause**: PyVis dependencies missing or HTML generation failed.

**Solution**:
1. Install PyVis: `pip install pyvis networkx`
2. Check the trace result_data for errors
3. Look for Python exceptions in Nautobot logs

## Performance Considerations

- **Synchronous Execution**: Traces currently run synchronously in a background thread
- **Polling Interval**: Status checked every 2 seconds
- **History Limit**: Shows last 50 traces per user

### Future Enhancements

- **Celery Integration**: Move trace execution to Celery for true async processing
- **WebSocket Updates**: Replace polling with WebSocket for real-time log streaming
- **Batch Tracing**: Trace multiple source/destination pairs in parallel
- **Export Options**: Download trace results as JSON, PDF, or CSV

## Integration with Network Provisioning

The Troubleshooting Studio integrates seamlessly with the Network Provisioning app:

- **Device Detail Pages**: Add "Troubleshoot Path" button
- **Interface Detail Pages**: Pre-populate source IP from interface
- **Execution Logs**: Link failed executions to troubleshooting traces
- **Automation Tasks**: Trigger traces as part of validation workflows

## Security & Permissions

- **Login Required**: All views require authentication
- **Permission Checks**: Respects Nautobot RBAC
  - `add_troubleshootingrecord`: Run new traces
  - `view_troubleshootingrecord`: View trace history
- **Credential Security**: Uses Nautobot SecretsGroups (never exposes passwords)
- **Audit Trail**: All traces logged with user, timestamp, and results

## Architecture Details

### SPA Island Pattern

The Troubleshooting Studio demonstrates the **SPA Island Pattern** for building application-style interfaces within Nautobot:

1. **Django Template** provides the shell and mounting point
2. **JavaScript App** handles all UI rendering and state management
3. **REST API** provides backend communication
4. **CSS Grid** creates full-screen, responsive layout

This pattern allows us to build rich, interactive UIs while maintaining Nautobot's authentication, navigation, and design language.

### Data Flow

```
User Input (Form)
  ↓
JavaScript App (troubleshooting_studio.js)
  ↓
REST API (TroubleshootingRunAPIView)
  ↓
NetworkPathTracer Service
  ↓
network_path_tracing Module
  ↓
Device Access (NAPALM, Netmiko, etc.)
  ↓
Results → TroubleshootingRecord
  ↓
Polling (JavaScript)
  ↓
Visualization (PyVis iframe)
```

## Contributing

To extend the Troubleshooting Studio:

1. **Add New Trace Types**: Extend `operation_type` choices in `TroubleshootingRecord`
2. **Custom Visualizations**: Replace PyVis with D3.js, Cytoscape, or React Flow
3. **Additional Platforms**: Add support for new device types in `network_path_tracing`
4. **Export Formats**: Add PDF, Visio, or draw.io export options

## References

- [Network Path Tracing Standalone Job](https://github.com/your-org/ansible-nautobot-network-path-troubleshooting)
- [PyVis Documentation](https://pyvis.readthedocs.io/)
- [Nautobot App Development](https://docs.nautobot.com/projects/core/en/stable/app-development/)
- [SPA Island Pattern](../AGENT_PROMPT/ui-designer-networking-prompt.md)

---

**Version**: 1.0.0  
**Last Updated**: December 26, 2025  
**Maintainer**: Network Automation Team


