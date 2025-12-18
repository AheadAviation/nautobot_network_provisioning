"""Jobs module for Network Provisioning (Automation) app.

Phase 2 will introduce a Job to execute queued `Execution` records asynchronously.
"""

from nautobot_network_provisioning.jobs.execution_processor import ExecutionProcessor
from nautobot_network_provisioning.jobs.demo_data_setup import DemoDataSetup
from nautobot_network_provisioning.jobs.git_sync import ExportAutomationToGit, ImportAutomationFromGit

jobs = [ExecutionProcessor, DemoDataSetup, ExportAutomationToGit, ImportAutomationFromGit]

__all__ = ["ExecutionProcessor", "DemoDataSetup", "ExportAutomationToGit", "ImportAutomationFromGit", "jobs"]
