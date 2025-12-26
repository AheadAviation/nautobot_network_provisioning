from nautobot.apps.ui import NavMenuTab, NavMenuGroup, NavMenuItem, NavMenuButton

menu_items = (
    NavMenuTab(
        name="Automation",
        groups=(
            NavMenuGroup(
                name="Automation Studio",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:studio_shell",
                        name="Studio",
                        permissions=["nautobot_network_provisioning.view_taskintent"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:taskintent_list",
                        name="Task Intents",
                        permissions=["nautobot_network_provisioning.view_taskintent"],
                        buttons=(
                            NavMenuButton(
                                link="plugins:nautobot_network_provisioning:task_studio_v2",
                                title="New Task",
                                icon_class="mdi mdi-plus-thick",
                                permissions=["nautobot_network_provisioning.add_taskintent"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:workflow_list",
                        name="Workflows",
                        permissions=["nautobot_network_provisioning.view_workflow"],
                        buttons=(
                            NavMenuButton(
                                link="plugins:nautobot_network_provisioning:workflow_studio",
                                title="New Workflow",
                                icon_class="mdi mdi-plus-thick",
                                permissions=["nautobot_network_provisioning.add_workflow"],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Automation Hub",
                weight=200,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:requestform_list",
                        name="Portals",
                        permissions=["nautobot_network_provisioning.view_requestform"],
                        buttons=(
                            NavMenuButton(
                                link="plugins:nautobot_network_provisioning:requestform_add",
                                title="New Portal",
                                icon_class="mdi mdi-plus-thick",
                                permissions=["nautobot_network_provisioning.add_requestform"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:portal",
                        name="Portal (Self-Service)",
                        permissions=["nautobot_network_provisioning.view_requestform"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:execution_list",
                        name="Execution History",
                        permissions=["nautobot_network_provisioning.view_execution"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Troubleshooting",
                weight=300,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:studio_tool_troubleshooting",
                        name="Path Trace",
                        permissions=["nautobot_network_provisioning.view_troubleshootingrecord"],
                    ),
                ),
            ),
        ),
    ),
)
