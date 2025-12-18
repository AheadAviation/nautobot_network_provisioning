"""Navigation menu for the Network Provisioning app."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Automation",
        weight=600,
        groups=(
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
                        link="plugins:nautobot_network_provisioning:taskimplementation_list",
                        name="Task Implementations",
                        weight=6,
                        permissions=["nautobot_network_provisioning.view_taskimplementation"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:taskimplementation_add",
                                permissions=["nautobot_network_provisioning.add_taskimplementation"],
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
                        link="plugins:nautobot_network_provisioning:workflowstep_list",
                        name="Workflow Steps",
                        weight=25,
                        permissions=["nautobot_network_provisioning.view_workflowstep"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:workflowstep_add",
                                permissions=["nautobot_network_provisioning.add_workflowstep"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:provider_list",
                        name="Providers",
                        weight=30,
                        permissions=["nautobot_network_provisioning.view_provider"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:provider_add",
                                permissions=["nautobot_network_provisioning.add_provider"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:providerconfig_list",
                        name="Provider Configs",
                        weight=40,
                        permissions=["nautobot_network_provisioning.view_providerconfig"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:providerconfig_add",
                                permissions=["nautobot_network_provisioning.add_providerconfig"],
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
                        link="plugins:nautobot_network_provisioning:requestformfield_list",
                        name="Request Form Fields",
                        weight=60,
                        permissions=["nautobot_network_provisioning.view_requestformfield"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:requestformfield_add",
                                permissions=["nautobot_network_provisioning.add_requestformfield"],
                            ),
                        ),
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
        ),
    ),
)


