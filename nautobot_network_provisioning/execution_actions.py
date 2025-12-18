"""Execution action views (Phase 4-5).

These are lightweight endpoints to:
- approve an execution (resume after approval step)
- request diff/apply operations (stored on execution.context["operation"])
"""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from nautobot_network_provisioning.models import Execution


def _require_auth(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Authentication required.")
    return None


class ExecutionApproveView(View):
    """Approve an execution and allow it to continue past approval steps."""

    def post(self, request, pk: str):
        resp = _require_auth(request)
        if resp:
            return resp
        if not request.user.has_perm("nautobot_network_provisioning.change_execution"):
            return HttpResponseForbidden("Permission denied.")

        exe = get_object_or_404(Execution, pk=pk)
        exe.approved_by = request.user
        if exe.status == Execution.StatusChoices.AWAITING_APPROVAL:
            exe.status = Execution.StatusChoices.PENDING
        exe.save(update_fields=["approved_by", "status", "last_updated"])
        messages.success(request, "Execution approved.")
        return redirect("plugins:nautobot_network_provisioning:execution", pk=exe.pk)


class ExecutionSetOperationView(View):
    """Set requested execution operation (render/diff/apply) and enqueue by setting pending."""

    def post(self, request, pk: str, operation: str):
        resp = _require_auth(request)
        if resp:
            return resp
        if not request.user.has_perm("nautobot_network_provisioning.change_execution"):
            return HttpResponseForbidden("Permission denied.")

        op = (operation or "").strip().lower()
        if op not in {"render", "diff", "apply"}:
            return HttpResponseForbidden("Invalid operation.")

        exe = get_object_or_404(Execution, pk=pk)
        exe.context = {**(exe.context or {}), "operation": op}
        if exe.status in {Execution.StatusChoices.COMPLETED, Execution.StatusChoices.FAILED, Execution.StatusChoices.CANCELLED}:
            # Don't auto-reset completed executions.
            messages.warning(request, f"Execution is {exe.status}; operation set but not queued.")
        else:
            exe.status = Execution.StatusChoices.PENDING
            messages.success(request, f"Execution queued for '{op}'.")
        exe.save(update_fields=["context", "status", "last_updated"])
        return redirect("plugins:nautobot_network_provisioning:execution", pk=exe.pk)


