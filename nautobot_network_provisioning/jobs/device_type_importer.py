"""Device type importer for NetAccess demo data.

This imports a small, curated set of device types from the upstream Nautobot
Device Type Library:

- https://github.com/nautobot/devicetype-library

The intent is to provide a realistic out-of-the-box demo where:
- DeviceTypes exist (with interface templates) for multiple platforms
- Demo devices can be created using real models

This module is designed to be called by the NetAccess demo data job.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import requests
import yaml
from nautobot.dcim.models import (
    ConsolePortTemplate,
    DeviceType,
    FrontPortTemplate,
    InterfaceTemplate,
    Manufacturer,
    PowerPortTemplate,
    RearPortTemplate,
)


DEVICETYPE_LIBRARY_BASE = "https://raw.githubusercontent.com/nautobot/devicetype-library"
DEFAULT_BRANCH = "main"


@dataclass(frozen=True)
class DeviceTypeRef:
    manufacturer: str
    model: str
    filename: str | None = None

    @property
    def yaml_filename(self) -> str:
        return self.filename or f"{self.model}.yaml"


DEFAULT_DEVICE_TYPES: list[DeviceTypeRef] = [
    # Cisco
    DeviceTypeRef(manufacturer="Cisco", model="C9200L-48P-4G"),
    DeviceTypeRef(manufacturer="Cisco", model="C9300-48P"),
    DeviceTypeRef(manufacturer="Cisco", model="C9500-24Y4C"),
    DeviceTypeRef(manufacturer="Cisco", model="N9K-C93180YC-FX"),
    # Arista
    DeviceTypeRef(manufacturer="Arista", model="DCS-7050SX3-48YC12"),
    DeviceTypeRef(manufacturer="Arista", model="DCS-7280SR-48C6"),
]


class DeviceTypeImportError(RuntimeError):
    """Raised when an import cannot proceed."""


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _raw_url(ref: DeviceTypeRef, *, branch: str = DEFAULT_BRANCH) -> str:
    # Format: https://raw.githubusercontent.com/nautobot/devicetype-library/<branch>/device-types/<Manufacturer>/<Model>.yaml
    return f"{DEVICETYPE_LIBRARY_BASE}/{branch}/device-types/{ref.manufacturer}/{ref.yaml_filename}"


def fetch_device_type_yaml(
    ref: DeviceTypeRef,
    *,
    branch: str = DEFAULT_BRANCH,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Fetch and parse a devicetype-library YAML file."""

    url = _raw_url(ref, branch=branch)
    resp = requests.get(url, timeout=timeout_seconds)
    resp.raise_for_status()
    data = yaml.safe_load(resp.text)

    if not isinstance(data, dict):
        raise DeviceTypeImportError(f"Invalid YAML for {ref.manufacturer}/{ref.model}: expected mapping")

    return data


def _upsert_device_type(
    *,
    manufacturer: Manufacturer,
    data: dict[str, Any],
    overwrite_existing: bool,
) -> DeviceType:
    model = data.get("model") or data.get("part_number") or "Unknown"

    defaults = {
        "model": model,
        "part_number": data.get("part_number") or "",
        "u_height": _safe_int(data.get("u_height"), default=1) or 1,
        "is_full_depth": bool(data.get("is_full_depth", True)),
        "comments": data.get("comments") or "",
    }

    device_type, created = DeviceType.objects.get_or_create(
        manufacturer=manufacturer,
        model=model,
        defaults=defaults,
    )

    if not created and overwrite_existing:
        # Update a small set of core fields; do not delete relationships.
        for field, value in defaults.items():
            setattr(device_type, field, value)
        device_type.save()

    return device_type


def _reset_templates_if_overwrite(device_type: DeviceType, overwrite_existing: bool) -> None:
    if not overwrite_existing:
        return

    # Clear existing templates so the imported YAML becomes the source of truth.
    InterfaceTemplate.objects.filter(device_type=device_type).delete()
    ConsolePortTemplate.objects.filter(device_type=device_type).delete()
    PowerPortTemplate.objects.filter(device_type=device_type).delete()
    RearPortTemplate.objects.filter(device_type=device_type).delete()
    FrontPortTemplate.objects.filter(device_type=device_type).delete()


def _create_interface_templates(device_type: DeviceType, data: dict[str, Any]) -> int:
    interfaces = data.get("interfaces") or []
    if not isinstance(interfaces, list):
        return 0

    created = 0
    for iface in interfaces:
        if not isinstance(iface, dict):
            continue
        name = iface.get("name")
        if not name:
            continue
        iface_type = iface.get("type") or "other"
        mgmt_only = bool(iface.get("mgmt_only", False))
        label = iface.get("label") or ""
        description = iface.get("description") or ""

        InterfaceTemplate.objects.get_or_create(
            device_type=device_type,
            name=name,
            defaults={
                "type": iface_type,
                "mgmt_only": mgmt_only,
                "label": label,
                "description": description,
            },
        )
        created += 1

    return created


def _create_console_ports(device_type: DeviceType, data: dict[str, Any]) -> int:
    ports = data.get("console-ports") or []
    if not isinstance(ports, list):
        return 0

    created = 0
    for port in ports:
        if not isinstance(port, dict):
            continue
        name = port.get("name")
        if not name:
            continue
        ConsolePortTemplate.objects.get_or_create(
            device_type=device_type,
            name=name,
            defaults={"type": port.get("type") or "other"},
        )
        created += 1
    return created


def _create_power_ports(device_type: DeviceType, data: dict[str, Any]) -> int:
    ports = data.get("power-ports") or []
    if not isinstance(ports, list):
        return 0

    created = 0
    for port in ports:
        if not isinstance(port, dict):
            continue
        name = port.get("name")
        if not name:
            continue
        PowerPortTemplate.objects.get_or_create(
            device_type=device_type,
            name=name,
            defaults={"type": port.get("type") or "iec-60320-c14"},
        )
        created += 1
    return created


def import_device_types(
    *,
    refs: Iterable[DeviceTypeRef] = DEFAULT_DEVICE_TYPES,
    overwrite_existing: bool = False,
    branch: str = DEFAULT_BRANCH,
    log: callable | None = None,
) -> list[DeviceType]:
    """Import a curated list of device types from the upstream device-type library.

    Args:
        refs: Device types to import.
        overwrite_existing: If True, update existing DeviceTypes and replace templates.
        branch: Git branch/tag in the upstream repo.
        log: Optional logging callable (e.g., job.logger.info).

    Returns:
        List of imported/created DeviceType objects.
    """

    imported: list[DeviceType] = []

    for ref in refs:
        try:
            data = fetch_device_type_yaml(ref, branch=branch)
        except Exception as exc:  # noqa: BLE001
            if log:
                log(f"DeviceType import: failed to fetch {ref.manufacturer}/{ref.model}: {exc}")
            continue

        manufacturer_name = data.get("manufacturer") or ref.manufacturer
        # Nautobot 2.3 uses Name as the natural key for Manufacturer (no slug field).
        manufacturer, _ = Manufacturer.objects.get_or_create(name=manufacturer_name)

        device_type = _upsert_device_type(
            manufacturer=manufacturer,
            data=data,
            overwrite_existing=overwrite_existing,
        )

        _reset_templates_if_overwrite(device_type, overwrite_existing)
        iface_count = _create_interface_templates(device_type, data)
        console_count = _create_console_ports(device_type, data)
        power_count = _create_power_ports(device_type, data)

        if log:
            log(
                "DeviceType import: "
                f"{manufacturer.name} {device_type.model} "
                f"(interfaces={iface_count}, console={console_count}, power={power_count})"
            )

        imported.append(device_type)

    return imported
