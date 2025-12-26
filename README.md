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

### Install Package

```bash
pip install nautobot-network-provisioning
```

### Configure Nautobot

Add `nautobot_network_provisioning` to your `PLUGINS` list in `nautobot_config.py`:

```python
PLUGINS = [
    "nautobot_network_provisioning",
    # ... other plugins
]
```

### Run Migrations

```bash
nautobot-server migrate
```

### Collect Static Files

```bash
nautobot-server collectstatic
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
