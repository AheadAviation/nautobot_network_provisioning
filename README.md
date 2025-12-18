# Nautobot Network Provisioning

[![CI](https://github.com/AheadAviation/nautobot_network_provisioning/actions/workflows/ci.yml/badge.svg)](https://github.com/AheadAviation/nautobot_network_provisioning/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/pypi/pyversions/nautobot-network-provisioning)](https://pypi.org/project/nautobot-network-provisioning/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A Nautobot App for Network Port Provisioning and MAC Address Tracking.

## Overview

Network Provisioning provides a comprehensive solution for managing network port configurations and tracking MAC addresses across your network infrastructure. It serves as a modern, Nautobot-integrated alternative to legacy port management tools (like TWIX/Back Box) within the Nautobot ecosystem.

### Key Features

- **Port Configuration Management**: Define service types (Access-VoIP, Access-Data, etc.) and apply standardized configurations to switch ports
- **Template-Based Configuration**: Use Jinja2-style templates with variable substitution for flexible port configurations
- **Work Queue System**: Schedule and track port configuration changes with approval workflows
- **MAC Address Tracking**: Comprehensive MAC address tracking with 30-day rolling history
- **ARP Table Integration**: Track IP-to-MAC mappings from network devices
- **Jack Mapping**: Map physical building/room/jack locations to network device interfaces
- **Bulk Import**: CSV import for jack mappings

## Installation

### From GitHub (Recommended)

```bash
pip install git+https://github.com/AheadAviation/nautobot_network_provisioning.git@v0.1.1
```

Or add to your `requirements.txt`:

```
nautobot-network-provisioning @ git+https://github.com/AheadAviation/nautobot_network_provisioning.git@v0.1.1
```

### From Source

```bash
git clone git@github.com:AheadAviation/nautobot_network_provisioning.git
cd nautobot_network_provisioning
pip install -e .
```

### Docker Installation

Add to your Dockerfile:

```dockerfile
# Install directly from GitHub
RUN pip install git+https://github.com/AheadAviation/nautobot_network_provisioning.git@v0.1.1

# Or copy locally and install
COPY ./nautobot_network_provisioning /tmp/nautobot_network_provisioning
RUN pip install /tmp/nautobot_network_provisioning
```

## Configuration

Add the app to your `nautobot_config.py`:

```python
PLUGINS = [
    "nautobot_network_provisioning",
]

PLUGINS_CONFIG = {
    "nautobot_network_provisioning": {
        "queue_processing_enabled": True,
        "write_mem_enabled": True,
        "mac_collection_enabled": True,
        "history_retention_days": 30,
        "demo_data": False,  # Set to True to enable demo data loader job
    },
}
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `queue_processing_enabled` | bool | `True` | Enable/disable work queue processing |
| `write_mem_enabled` | bool | `True` | Save configuration after applying changes |
| `config_backup_enabled` | bool | `True` | Backup config before making changes |
| `dry_run_default` | bool | `True` | Default to dry-run mode for new queue entries |
| `max_queue_entries_per_run` | int | `50` | Max queue entries per job run |
| `mac_collection_enabled` | bool | `True` | Enable/disable MAC address collection jobs |
| `history_retention_days` | int | `30` | Days to retain MAC address history |
| `demo_data` | bool | `False` | Enable demo data loader job |
| `validate_templates_on_save` | bool | `True` | Validate Jinja2 syntax on template save |

## Database Migrations

After installation, run migrations:

```bash
nautobot-server migrate
```

## Usage

### Services

Services define the types of port configurations available (e.g., "Access-VoIP", "Access-Data", "Trunk-Uplink").

Navigate to: **Network Provisioning > Configuration > Services**

### Switch Profiles

Switch profiles define device type patterns and OS version patterns to match templates to specific switch types.

Navigate to: **Network Provisioning > Configuration > Switch Profiles**

### Config Templates

Configuration templates define the actual commands to apply to interfaces. Templates support variable substitution using Jinja2 or legacy TWIX syntax:

| Variable | Jinja2 | Legacy TWIX | Description |
|----------|--------|-------------|-------------|
| Interface | `{{ interface }}` | `__INTERFACE__` | Interface name |
| Switch | `{{ device.name }}` | `__SWITCH__` | Device name |
| Building | `{{ building }}` | `__BUILDING__` | Building name |
| Room | `{{ comm_room }}` | `__COMM_ROOM__` | Communication room |
| Jack | `{{ jack }}` | `__JACK__` | Jack identifier |
| Service | `{{ service.name }}` | `__SERVICE__` | Service name |
| VLAN | `{{ vlan }}` or `{{ data_vlan }}` | `__VLAN__` | VLAN ID |

### Jack Mappings

Map physical building/room/jack locations to network device interfaces.

Navigate to: **Network Provisioning > Configuration > Jack Mappings**

#### CSV Import Format

```csv
building,comm_room,jack,device_name,interface_name,description
Science Building,MDF-040,0228,switch-01,GigabitEthernet1/0/1,Lab 401
```

### Work Queue

The work queue tracks pending, in-progress, completed, and failed port configuration changes.

Navigate to: **Network Provisioning > Operations > Work Queue**

### MAC Address Tracking

View learned MAC addresses, their current locations, and historical movements.

Navigate to: **Network Provisioning > MAC Tracking > MAC Addresses**

## Jobs

### Load Demo Data

Populates the database with example services, profiles, templates, and MAC data.

- **Type**: On-demand
- **Control Setting**: `demo_data` must be `True`

### Work Queue Processor

Processes pending work queue entries and applies configurations to devices.

- **Schedule**: Every 5 minutes (recommended)
- **Control Setting**: `queue_processing_enabled`

### MAC Address Collector

Collects MAC address tables from network devices.

- **Schedule**: Every 15-30 minutes (recommended)
- **Control Setting**: `mac_collection_enabled`

### ARP Collector

Collects ARP tables from Layer 3 devices.

- **Schedule**: Every 30 minutes (recommended)
- **Control Setting**: `mac_collection_enabled`

### MAC History Archiver

Removes MAC address history older than the retention period.

- **Schedule**: Daily (recommended)
- **Control Setting**: `history_retention_days`

### Jack Mapping Import

Bulk import jack mappings from CSV files.

- **Type**: On-demand

## Device Credentials

The app retrieves device credentials in the following order:

1. **Nautobot Secrets Group**: If the device has an assigned secrets group
2. **Environment Variables**:
   - `NAUTOBOT_NAPALM_USERNAME`
   - `NAUTOBOT_NAPALM_PASSWORD`
   - `NAUTOBOT_NAPALM_ARGS` (for enable secret)

## REST API

All models are exposed via the REST API:

- `GET/POST /api/plugins/network-provisioning/services/`
- `GET/POST /api/plugins/network-provisioning/switch-profiles/`
- `GET/POST /api/plugins/network-provisioning/config-templates/`
- `GET/POST /api/plugins/network-provisioning/jack-mappings/`
- `GET/POST /api/plugins/network-provisioning/work-queue-entries/`
- `GET/POST /api/plugins/network-provisioning/mac-addresses/`
- `GET /api/plugins/network-provisioning/mac-address-entries/`
- `GET /api/plugins/network-provisioning/mac-address-history/`
- `GET /api/plugins/network-provisioning/arp-entries/`
- `GET/POST /api/plugins/network-provisioning/control-settings/`

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone git@github.com:AheadAviation/nautobot_network_provisioning.git
cd nautobot_network_provisioning

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nautobot_network_provisioning --cov-report=html
```

### Code Quality

```bash
# Format code
black nautobot_network_provisioning/
isort nautobot_network_provisioning/

# Lint
ruff check nautobot_network_provisioning/
```

### Pre-commit (recommended)

```bash
pip install -e ".[dev]"
pre-commit install
pre-commit run -a
```

## Versioning

This project uses [Semantic Versioning](https://semver.org/).

To release a new version:

1. Run the "Version Bump" workflow in GitHub Actions
2. Merge the resulting PR
3. Create a tag `v{version}` to trigger a release

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/AheadAviation/nautobot_network_provisioning/issues)
- **Documentation**: [GitHub Wiki](https://github.com/AheadAviation/nautobot_network_provisioning/wiki)
