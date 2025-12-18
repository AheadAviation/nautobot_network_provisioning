"""TaskImplementation selection logic (Manufacturer → Platform → SoftwareVersion → priority)."""

from __future__ import annotations

from typing import Optional

from nautobot_network_provisioning.models import TaskDefinition, TaskImplementation


def _software_matches(impl: TaskImplementation, software_version) -> bool:
    """
    If impl has software_versions set, require membership.
    If impl has no software_versions restriction, match all.
    """
    if impl.software_versions.count() == 0:
        return True
    if not software_version:
        return False
    return impl.software_versions.filter(pk=software_version.pk).exists()


def select_task_implementation(
    *,
    task: TaskDefinition,
    manufacturer,
    platform=None,
    software_version=None,
) -> Optional[TaskImplementation]:
    """
    Select the best matching TaskImplementation for the given device attributes.

    Selection logic (design-aligned):
    - Filter by task + manufacturer (required)
    - If platform provided, prefer platform-specific over generic (platform=None)
    - If software_version_pattern provided, require match
    - Highest priority wins (ties broken by name)
    """
    qs = TaskImplementation.objects.filter(task=task, manufacturer=manufacturer, enabled=True)

    # Split into platform-specific and generic
    platform_specific = qs.filter(platform=platform) if platform else TaskImplementation.objects.none()
    generic = qs.filter(platform__isnull=True)

    candidates = list(platform_specific.order_by("-priority", "name")) + list(generic.order_by("-priority", "name"))
    for impl in candidates:
        if _software_matches(impl, software_version):
            return impl
    return None


