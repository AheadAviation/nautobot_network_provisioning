# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2025-12-17

### Fixed

- Packaged the plugin as a proper Python module (`nautobot_network_provisioning/`) so `pip install` and GitHub Actions can import it.
- Release workflow now builds/releases from an installable package layout.

## [0.1.0] - 2025-12-17

### Added

- Initial release of Network Provisioning for Nautobot
- **Port Configuration Management**
  - Port Services (AP, VOIP, Data, Trunk, etc.)
  - Switch Profiles for device matching
  - Config Templates with Jinja2 and legacy TWIX syntax support
  - Template versioning with effective dates
- **Work Queue System**
  - Scheduled configuration changes
  - Dry-run mode for testing
  - Automatic config backup before changes
  - Integration with Napalm/Netmiko for device configuration
- **MAC Address Tracking**
  - MAC address collection from network devices
  - 30-day history retention
  - ARP entry correlation
  - Interface-level tracking
- **Jack Mapping**
  - Building/Room/Jack to Device/Interface mapping
  - Bulk import from CSV
- **Demo Data Loader**
  - Comprehensive demo data for testing
  - Support for Cisco IOS, NX-OS, and Arista EOS templates
- **API Endpoints**
  - Full REST API for all models
  - GraphQL support via Nautobot

### Changed

- Renamed from `nautobot_netaccess` to `nautobot_network_provisioning`

### Deprecated

- Legacy `software_version` ForeignKey on ConfigTemplate (use `software_versions` M2M field)

[Unreleased]: https://github.com/AheadAviation/nautobot_network_provisioning/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/AheadAviation/nautobot_network_provisioning/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AheadAviation/nautobot_network_provisioning/releases/tag/v0.1.0
