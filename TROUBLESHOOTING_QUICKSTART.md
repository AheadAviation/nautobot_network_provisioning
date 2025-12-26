# Quick Start: Testing the Troubleshooting Studio

## Prerequisites

You need to have the standalone `network-path-troubleshooting` job accessible to Nautobot.

## Step 1: Install Dependencies

```bash
pip install pyvis networkx napalm netmiko
```

## Step 2: Make network_path_tracing Module Available

**Option A: Add to PYTHONPATH (Temporary)**
```bash
export PYTHONPATH="C:\Users\BrianNelson\Projects\ansible-nautobot-network-path-troubleshooting\jobs:$PYTHONPATH"
```

**Option B: Copy to Site-Packages (Permanent)**
```bash
# Find your site-packages directory
python -c "import site; print(site.getsitepackages())"

# Copy the module
cp -r C:\Users\BrianNelson\Projects\ansible-nautobot-network-path-troubleshooting\jobs\network_path_tracing \
      /path/to/site-packages/
```

**Option C: Create Symlink**
```bash
ln -s C:\Users\BrianNelson\Projects\ansible-nautobot-network-path-troubleshooting\jobs\network_path_tracing \
      /path/to/site-packages/network_path_tracing
```

## Step 3: Run Migrations

```bash
cd C:\Users\BrianNelson\Projects\nautobot_network_provisioning
nautobot-server migrate nautobot_network_provisioning
```

## Step 4: Setup Status Objects

```bash
nautobot-server setup_troubleshooting
```

This creates the required Status objects (pending, running, completed, failed).

## Step 5: Verify Installation

```bash
# Test that the module is importable
python -c "import network_path_tracing; print('✓ Module found')"

# Start Nautobot development server
nautobot-server runserver 0.0.0.0:8080
```

## Step 6: Access the Studio

Open your browser and navigate to:
```
http://localhost:8080/plugins/network-provisioning/studio/tools/troubleshooting/
```

## Step 7: Run Your First Trace

1. **Enter Source IP**: Use an IP from your Nautobot IPAM (e.g., `10.0.0.1`)
2. **Enter Destination IP**: Any IP or FQDN (e.g., `8.8.8.8` or `google.com`)
3. **Select Secrets Group**: Choose a SecretsGroup with device credentials
4. **Click "Run Trace"**

Watch the logs in real-time as the trace progresses!

## Troubleshooting

### "Network path tracing module is not available"

The `network_path_tracing` module is not in your Python path. Try:

```bash
# Verify the module exists
ls C:\Users\BrianNelson\Projects\ansible-nautobot-network-path-troubleshooting\jobs\network_path_tracing

# Test import
python -c "import sys; sys.path.insert(0, 'C:\\Users\\BrianNelson\\Projects\\ansible-nautobot-network-path-troubleshooting\\jobs'); import network_path_tracing; print('OK')"
```

### "Status matching query does not exist"

Run the setup command:
```bash
nautobot-server setup_troubleshooting
```

### "SecretsGroup has no username/password"

1. Go to Nautobot UI → Secrets → Secrets Groups
2. Edit your SecretsGroup
3. Add Generic/Username and Generic/Password secrets

### Trace hangs or fails

Check the Nautobot logs:
```bash
tail -f /opt/nautobot/nautobot.log
```

Look for Python exceptions or device connection errors.

## Next Steps

- Read the full documentation: `nautobot_network_provisioning/docs/TROUBLESHOOTING_STUDIO.md`
- Run test scenarios: `nautobot_network_provisioning/docs/TROUBLESHOOTING_TESTING.md`
- Review the implementation: `nautobot_network_provisioning/docs/TROUBLESHOOTING_IMPLEMENTATION_SUMMARY.md`

## Quick Reference

### URLs

- **Studio**: `/plugins/network-provisioning/studio/tools/troubleshooting/`
- **API Run**: `/plugins/network-provisioning/api/troubleshooting/run/`
- **API Status**: `/plugins/network-provisioning/api/troubleshooting/status/<uuid>/`
- **API History**: `/plugins/network-provisioning/api/troubleshooting/history/`

### Files Created

- `models/troubleshooting.py` - TroubleshootingRecord model
- `services/troubleshooting.py` - NetworkPathTracer service
- `troubleshooting_views.py` - Views and API endpoints
- `templates/studio_tools/troubleshooting_studio.html` - SPA shell
- `static/css/troubleshooting_studio.css` - Layout CSS
- `static/js/troubleshooting_studio.js` - JavaScript app
- `migrations/0005_troubleshootingrecord.py` - Database migration
- `management/commands/setup_troubleshooting.py` - Setup command

### Key Features

✅ Real-time trace execution with live logs  
✅ Interactive PyVis network visualization  
✅ Trace history with one-click reload  
✅ REST API for automation  
✅ Responsive design (desktop/tablet/mobile)  
✅ Full integration with Nautobot RBAC  

---

**Ready to troubleshoot your network!** 🚀


