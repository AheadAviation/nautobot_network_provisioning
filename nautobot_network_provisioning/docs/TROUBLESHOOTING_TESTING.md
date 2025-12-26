# Testing the Troubleshooting Studio

This guide walks you through testing the Network Path Troubleshooting Studio end-to-end.

## Prerequisites Checklist

Before testing, ensure you have:

- [ ] Nautobot Network Provisioning app installed
- [ ] Migrations run: `nautobot-server migrate`
- [ ] Status objects created: `nautobot-server setup_troubleshooting`
- [ ] Network path tracing dependencies installed: `pip install pyvis networkx napalm netmiko`
- [ ] `network_path_tracing` module in Python path
- [ ] At least one SecretsGroup with Generic username/password
- [ ] At least one device with primary IP in Nautobot
- [ ] At least one prefix with a gateway tagged `network_gateway = True`

## Quick Setup for Testing

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install pyvis networkx napalm netmiko

# Copy network_path_tracing module (adjust paths as needed)
export PYTHONPATH="/path/to/ansible-nautobot-network-path-troubleshooting/jobs:$PYTHONPATH"
```

### 2. Run Setup Command

```bash
nautobot-server setup_troubleshooting
```

This creates the required Status objects.

### 3. Create Test Data

```python
# In Nautobot shell (nautobot-server nbshell)
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.dcim.models import Device
from nautobot.extras.models import SecretsGroup, Secret
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices

# Create a test prefix
prefix = Prefix.objects.create(
    prefix='10.0.0.0/24',
    status=Status.objects.get(slug='active')
)

# Create a gateway IP and tag it
gateway = IPAddress.objects.create(
    address='10.0.0.1/24',
    status=Status.objects.get(slug='active')
)
gateway.cf['network_gateway'] = True
gateway.save()

# Create a test device
device = Device.objects.create(
    name='test-router-01',
    device_type=DeviceType.objects.first(),
    role=DeviceRole.objects.first(),
    site=Site.objects.first(),
    status=Status.objects.get(slug='active')
)

# Assign primary IP to device
device.primary_ip4 = gateway
device.save()

# Create a SecretsGroup (if you don't have one)
secrets_group = SecretsGroup.objects.create(name='Test Credentials')

# Add username secret
username_secret = Secret.objects.create(
    name='Test Username',
    provider='environment-variable',
    parameters={'variable': 'TEST_USERNAME'}
)
secrets_group.secrets.create(
    access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
    secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
    secret=username_secret
)

# Add password secret
password_secret = Secret.objects.create(
    name='Test Password',
    provider='environment-variable',
    parameters={'variable': 'TEST_PASSWORD'}
)
secrets_group.secrets.create(
    access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
    secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
    secret=password_secret
)
```

## Test Scenarios

### Test 1: Access the Studio

**Steps:**
1. Navigate to `http://localhost:8080/plugins/network-provisioning/studio/tools/troubleshooting/`
2. Verify the page loads without errors
3. Check that the form is visible on the left
4. Check that the visualization area is visible on the right

**Expected Result:**
- Page loads successfully
- No JavaScript console errors
- Form displays with all fields
- Placeholder message shows in visualization area

### Test 2: Run a Simple Trace

**Steps:**
1. Enter source IP: `10.0.0.1`
2. Enter destination IP: `8.8.8.8`
3. Select a SecretsGroup
4. Check "Enable Layer 2 Discovery"
5. Click "Run Trace"

**Expected Result:**
- Button changes to "Running..." with spinner
- Progress bar appears at top of visualization
- Live logs appear in bottom panel
- Status updates every 2 seconds
- On completion:
  - Button returns to "Run Trace"
  - Progress bar disappears
  - Visualization loads in iframe
  - Success message in logs
  - New entry appears in history

### Test 3: View Trace History

**Steps:**
1. Run 2-3 traces with different source/destination pairs
2. Click on a previous trace in the history panel

**Expected Result:**
- Clicked item highlights with blue background
- Visualization updates to show selected trace
- Logs display summary of selected trace
- Status indicator updates

### Test 4: Test with FQDN

**Steps:**
1. Enter source IP: `10.0.0.1`
2. Enter destination: `google.com` (FQDN)
3. Select SecretsGroup
4. Click "Run Trace"

**Expected Result:**
- Logs show hostname resolution: "Resolved destination hostname 'google.com' to IPv4 address X.X.X.X"
- Trace proceeds normally with resolved IP

### Test 5: Test Error Handling

**Steps:**
1. Enter invalid source IP: `999.999.999.999`
2. Click "Run Trace"

**Expected Result:**
- Error message appears in logs
- Status shows "Failed"
- No visualization loads
- Error details visible in result_data

### Test 6: Test API Endpoints

**Using curl or Postman:**

```bash
# Run a trace
curl -X POST http://localhost:8080/plugins/network-provisioning/api/troubleshooting/run/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "source_ip": "10.0.0.1",
    "destination_ip": "8.8.8.8",
    "secrets_group_id": "YOUR_SECRETS_GROUP_UUID",
    "enable_layer2_discovery": true,
    "ping_endpoints": false
  }'

# Check status
curl http://localhost:8080/plugins/network-provisioning/api/troubleshooting/status/RECORD_UUID/ \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"

# Get history
curl http://localhost:8080/plugins/network-provisioning/api/troubleshooting/history/ \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

**Expected Result:**
- POST returns `{"record_id": "...", "status": "running"}`
- GET status returns complete record details
- GET history returns array of records

### Test 7: Test Visualization Interactivity

**Steps:**
1. Run a trace that completes successfully
2. Wait for visualization to load
3. Hover over nodes in the graph
4. Hover over edges in the graph
5. Try dragging nodes
6. Try zooming in/out

**Expected Result:**
- Hover shows tooltip with node/edge details
- Nodes can be dragged (if physics enabled)
- Graph can be zoomed with mouse wheel
- Graph can be panned by dragging background

### Test 8: Test Responsive Design

**Steps:**
1. Open the studio in a desktop browser (1920x1080)
2. Resize browser to tablet size (768x1024)
3. Resize to mobile size (375x667)

**Expected Result:**
- Desktop: 2-column layout (form left, viz right)
- Tablet: 2-column layout with narrower form panel
- Mobile: Stacked layout (form top, viz bottom)

### Test 9: Test Concurrent Traces

**Steps:**
1. Open studio in two browser tabs
2. Run a trace in Tab 1
3. While Tab 1 is running, run a trace in Tab 2

**Expected Result:**
- Both traces run independently
- Each tab shows its own trace progress
- History updates in both tabs after completion

### Test 10: Test Permissions

**Steps:**
1. Log in as a user without `add_troubleshootingrecord` permission
2. Try to access the studio

**Expected Result:**
- User can view the page (if they have `view_troubleshootingrecord`)
- Run button is disabled or shows permission error
- User cannot submit traces

## Troubleshooting Test Failures

### "Network path tracing module is not available"

**Fix:**
```bash
# Verify module is importable
python -c "import network_path_tracing; print('OK')"

# If not, add to PYTHONPATH
export PYTHONPATH="/path/to/ansible-nautobot-network-path-troubleshooting/jobs:$PYTHONPATH"

# Restart Nautobot
nautobot-server restart
```

### Trace hangs at "Running..."

**Debug:**
1. Check Nautobot logs: `tail -f /opt/nautobot/nautobot.log`
2. Look for Python exceptions
3. Verify device is reachable: `ping DEVICE_IP`
4. Test SSH manually: `ssh username@DEVICE_IP`

### Visualization doesn't load

**Debug:**
1. Check browser console for JavaScript errors
2. Verify PyVis is installed: `pip list | grep pyvis`
3. Check if `interactive_html` field is populated in database:
   ```python
   from nautobot_network_provisioning.models import TroubleshootingRecord
   record = TroubleshootingRecord.objects.latest('start_time')
   print(len(record.interactive_html))  # Should be > 0
   ```

### Status stuck at "Running"

**Fix:**
```python
# Manually update stuck records
from nautobot_network_provisioning.models import TroubleshootingRecord
from nautobot.extras.models import Status

failed_status = Status.objects.get(slug='failed')
stuck_records = TroubleshootingRecord.objects.filter(status__slug='running')
for record in stuck_records:
    record.status = failed_status
    record.result_data = {'error': 'Trace timed out or was interrupted'}
    record.save()
```

## Performance Testing

### Load Test

**Test 100 concurrent traces:**

```python
import requests
import threading
import time

def run_trace(i):
    response = requests.post(
        'http://localhost:8080/plugins/network-provisioning/api/troubleshooting/run/',
        json={
            'source_ip': '10.0.0.1',
            'destination_ip': f'8.8.{i % 256}.{i % 256}',
            'secrets_group_id': 'YOUR_UUID',
            'enable_layer2_discovery': False,
            'ping_endpoints': False,
        },
        headers={'X-CSRFToken': 'YOUR_TOKEN'}
    )
    print(f"Trace {i}: {response.status_code}")

threads = []
start = time.time()
for i in range(100):
    t = threading.Thread(target=run_trace, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"Completed 100 traces in {time.time() - start:.2f} seconds")
```

**Expected Result:**
- All traces complete without errors
- Average completion time < 30 seconds per trace
- No memory leaks or database connection issues

## Automated Testing

### Unit Tests

Create `nautobot_network_provisioning/tests/test_troubleshooting.py`:

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from nautobot.extras.models import Status, SecretsGroup
from nautobot_network_provisioning.models import TroubleshootingRecord

User = get_user_model()


class TroubleshootingStudioTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        # Create required statuses
        for slug in ['pending', 'running', 'completed', 'failed']:
            Status.objects.create(slug=slug, name=slug.title())
    
    def test_studio_page_loads(self):
        response = self.client.get('/plugins/network-provisioning/studio/tools/troubleshooting/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'troubleshooting-studio-root')
    
    def test_api_run_requires_auth(self):
        self.client.logout()
        response = self.client.post('/plugins/network-provisioning/api/troubleshooting/run/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_api_history(self):
        response = self.client.get('/plugins/network-provisioning/api/troubleshooting/history/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('records', data)
```

Run tests:
```bash
nautobot-server test nautobot_network_provisioning.tests.test_troubleshooting
```

## Success Criteria

All tests pass if:

- [ ] Studio page loads without errors
- [ ] Traces can be run successfully
- [ ] Visualizations render correctly
- [ ] History panel updates properly
- [ ] API endpoints return expected responses
- [ ] Error handling works correctly
- [ ] Responsive design works on all screen sizes
- [ ] Permissions are enforced
- [ ] No memory leaks or performance issues
- [ ] Unit tests pass

## Next Steps

After successful testing:

1. **Production Deployment**:
   - Set up Celery for async trace execution
   - Configure monitoring and alerting
   - Set up log aggregation

2. **User Training**:
   - Create user documentation
   - Record demo videos
   - Conduct training sessions

3. **Integration**:
   - Add "Troubleshoot" buttons to Device/Interface detail pages
   - Integrate with automation workflows
   - Set up scheduled traces for monitoring

---

**Happy Testing!** 🎉


