"""Job to process pending Executions (Phase 2)."""

from __future__ import annotations

from nautobot.apps.jobs import Job

from nautobot_network_provisioning.models import Execution
from nautobot_network_provisioning.services.execution_engine import run_execution


class ExecutionProcessor(Job):
    """Processor for pending/scheduled Executions."""

    class Meta:  # noqa: D106
        name = "Execution Processor"
        description = "Process pending/scheduled Executions (render/diff/apply)."

    def run(self, limit: int = 25, operation: str = "render"):  # noqa: D102
        qs = Execution.objects.filter(status__in=[Execution.StatusChoices.PENDING, Execution.StatusChoices.SCHEDULED]).order_by(
            "created"
        )
        total = qs.count()
        processed = 0

        for execution in qs[: max(1, int(limit))]:
            processed += 1
            self.logger.info("Processing Execution %s (%s)", execution.pk, execution.workflow_id)
            op = (execution.context or {}).get("operation") or operation
            run_execution(execution, operation=str(op))

        return f"Processed {processed}/{total} pending executions."


