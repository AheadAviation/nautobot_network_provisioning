"""Navigation menu for the Network Provisioning app."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Automation",
        weight=600,
        groups=(
            NavMenuGroup(
                name="Dashboard",
                weight=50,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:home",
                        name="Home",
                        weight=10,
                        permissions=["nautobot_network_provisioning.view_taskdefinition"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Authoring",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:taskdefinition_list",
                        name="Task Catalog",
                        weight=5,
                        permissions=["nautobot_network_provisioning.view_taskdefinition"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:taskdefinition_add",
                                permissions=["nautobot_network_provisioning.add_taskdefinition"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:workflow_list",
                        name="Workflows",
                        weight=20,
                        permissions=["nautobot_network_provisioning.view_workflow"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:workflow_add",
                                permissions=["nautobot_network_provisioning.add_workflow"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:requestform_list",
                        name="Request Forms",
                        weight=50,
                        permissions=["nautobot_network_provisioning.view_requestform"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:requestform_add",
                                permissions=["nautobot_network_provisioning.add_requestform"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:template_ide",
                        name="Template IDE",
                        weight=60,
                        permissions=["nautobot_network_provisioning.view_taskimplementation"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Integrations",
                weight=210,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:provider_list",
                        name="Connection Providers",
                        weight=10,
                        permissions=["nautobot_network_provisioning.view_provider"],
                    ),
                    NavMenuItem(
                        link="extras:gitrepository_list",
                        name="Git Repositories",
                        weight=20,
                        permissions=["extras.view_gitrepository"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Portal",
                weight=200,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:portal",
                        name="Portal",
                        weight=10,
                        permissions=["nautobot_network_provisioning.view_requestform"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Executions",
                weight=250,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:execution_list",
                        name="Executions",
                        weight=10,
                        permissions=["nautobot_network_provisioning.view_execution"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Maintenance",
                weight=300,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:taskimplementation_list",
                        name="Raw Implementations",
                        weight=5,
                        permissions=["nautobot_network_provisioning.view_taskimplementation"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:workflowstep_list",
                        name="Raw Workflow Steps",
                        weight=10,
                        permissions=["nautobot_network_provisioning.view_workflowstep"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:requestformfield_list",
                        name="Raw Form Fields",
                        weight=15,
                        permissions=["nautobot_network_provisioning.view_requestformfield"],
                    ),
                    NavMenuItem(
                        link="extras:job_list",
                        name="System Jobs",
                        weight=20,
                        permissions=["extras.view_job"],
                    ),
                ),
            ),
        ),
    ),
)


