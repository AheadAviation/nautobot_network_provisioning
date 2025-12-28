# Nautobot Network Provisioning App

A comprehensive **Network Automation Hub** for Nautobot. It serves as the **automation and execution arm** of Nautobot, enabling low-code/UI-first authoring of reusable tasks and workflows.

## Overview

The Nautobot Network Provisioning App transforms Nautobot from a passive Source of Truth into an active Network Automation platform. It provides a visual authoring environment for creating platform-agnostic network automation tasks, chaining them into complex workflows, and exposing them to users through a self-service portal.

## Key Features

-   **Visual Task Studio**: Author network automation tasks using Jinja2 templates and platform-specific drivers (Netmiko, NAPALM).
-   **Workflow Designer**: Chain tasks together into multi-step automation workflows with conditional logic.
-   **SPA Island Architecture**: Modern, high-performance UI for studio views that integrate seamlessly with Nautobot.
-   **Self-Service Portal**: Expose workflows to end-users via customizable request forms.
-   **Execution Engine**: Real-time execution tracking with detailed logging and audit trails.
-   **Live Troubleshooting**: Real-time network path tracing and visualization.
-   **GitOps Ready**: Synchronize your task library with Git repositories.

## Core Concepts

-   **Task**: A single unit of automation (e.g., "Configure NTP", "Create VLAN").
-   **Strategy**: A platform-specific implementation of a task (e.g., "Cisco IOS", "Arista EOS").
-   **Workflow**: A collection of tasks executed in sequence.
-   **Request Form**: A user-facing form that triggers a workflow with specific inputs.
-   **Execution**: A record of a workflow or task run, including logs and results.

## Installation

### Prerequisites

-   Nautobot 2.0 or higher
-   Python 3.8 or higher

### Installation (Private Repository)

Since this app is currently hosted in a private repository, you must install it directly from Git.

#### Prerequisites
- **Git** must be installed on your system.
- You must have **access permissions** to the private repository.

#### Method 1: Via SSH (Recommended)
This is the most secure method. Ensure your SSH key is added to your GitHub account.
```bash
pip install git+ssh://git@github.com/AheadAviation/nautobot_network_provisioning.git@main
```

#### Method 2: Via HTTPS (Using a Personal Access Token)
If you do not have SSH keys configured, you can use a [Personal Access Token (PAT)](https://github.com/settings/tokens):
1. Create a PAT with `repo` scope.
2. Use the token in the installation command:
```bash
pip install git+https://<YOUR_TOKEN>@github.com/AheadAviation/nautobot_network_provisioning.git@main
```

#### Method 3: Via HTTPS (Public Repository)
If the repository is public:
```bash
pip install git+https://github.com/AheadAviation/nautobot_network_provisioning.git@main
```

### Configure Nautobot

Add `nautobot_network_provisioning` to your `PLUGINS` list in `nautobot_config.py`:

```python
PLUGINS = [
    "nautobot_network_provisioning",
    # ... other plugins
]

PLUGINS_CONFIG = {
    "nautobot_network_provisioning": {
        "demo_data": False,  # Set to True for demo data
        "queue_processing_enabled": True,
        "write_mem_enabled": True,
        "mac_collection_enabled": True,
        "history_retention_days": 30,
        "proxy_worker_enabled": False,
        "proxy_broker_url": "redis://localhost:6379/0",
        "proxy_backend_url": "redis://localhost:6379/0",
        "proxy_queue_name": "proxy_queue",
        "proxy_task_timeout": 120,
    },
}
```

### Run Migrations

```bash
nautobot-server migrate
```

### Collect Static Files

```bash
nautobot-server collectstatic
```

### Installation with Docker

If you're using Docker, add the app to your `requirements.txt`:

```
git+https://github.com/AheadAviation/nautobot_network_provisioning.git@main
```

Or if using a private repository with a token:

```
git+https://<YOUR_TOKEN>@github.com/AheadAviation/nautobot_network_provisioning.git@main
```

**Using Build Arguments (Recommended for Private Repos):**

1. Update your `Dockerfile`:
```dockerfile
ARG GITHUB_TOKEN
RUN pip install git+https://${GITHUB_TOKEN}@github.com/AheadAviation/nautobot_network_provisioning.git@main
```

2. Build with the token:
```bash
docker build --build-arg GITHUB_TOKEN=your_token_here -t my-nautobot-image .
```

3. Using `docker-compose.yml`:
```yaml
services:
  nautobot:
    build:
      context: .
      args:
        - GITHUB_TOKEN=${GITHUB_TOKEN}
```

Then rebuild your Docker image:
```bash
docker-compose build --no-cache nautobot
docker-compose up -d
```

## Quick Start

1.  Navigate to **Automation > Studio** to start creating tasks.
2.  Import existing tasks from the **Task Library Sync** job.
3.  Create a **Workflow** by chaining imported tasks.
4.  Publish a **Request Form** to the **Automation Portal**.

## Development

We recommend using the provided Docker-based development environment in the sibling `nautobot_docker` repository.

### Setup

1.  Clone the repository.
2.  Run `pip install -e .` for local development.
3.  Use the `reload_local_plugin.sh` script in `nautobot_docker` to refresh your environment.

## Documentation

Comprehensive documentation can be found in the [docs/](docs/) directory.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.
