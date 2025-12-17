"""Navigation menu for the NetAccess app."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Network Access",
        weight=600,
        groups=(
            NavMenuGroup(
                name="Configuration",
                weight=100,
                items=(
                    # Automated Tasks - Groups templates by purpose (Primary)
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:portservice_list",
                        name="Automated Tasks",
                        weight=100,
                        permissions=["nautobot_network_provisioning.view_portservice"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:portservice_add",
                                permissions=["nautobot_network_provisioning.add_portservice"],
                            ),
                        ),
                    ),
                    # Templates - All config templates with preview
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:configtemplate_list",
                        name="Config Templates",
                        weight=200,
                        permissions=["nautobot_network_provisioning.view_configtemplate"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:configtemplate_add",
                                permissions=["nautobot_network_provisioning.add_configtemplate"],
                            ),
                        ),
                    ),
                    # Template IDE - GraphiQL-style editor
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:template_ide",
                        name="Template IDE",
                        weight=250,
                        permissions=["nautobot_network_provisioning.view_configtemplate"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Work Queue",
                weight=150,
                items=(
                    # New Port Config Request (TWIX-style)
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:port_config_request",
                        name="New Request",
                        weight=50,
                        permissions=["nautobot_network_provisioning.add_workqueueentry"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:workqueueentry_list",
                        name="Queue Entries",
                        weight=100,
                        permissions=["nautobot_network_provisioning.view_workqueueentry"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:workqueueentry_add",
                                permissions=["nautobot_network_provisioning.add_workqueueentry"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:jackmapping_list",
                        name="Jack Mappings",
                        weight=200,
                        permissions=["nautobot_network_provisioning.view_jackmapping"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:jackmapping_add",
                                permissions=["nautobot_network_provisioning.add_jackmapping"],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="MAC Tracking",
                weight=200,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:macaddress_list",
                        name="MAC Addresses",
                        weight=100,
                        permissions=["nautobot_network_provisioning.view_macaddress"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:macaddress_add",
                                permissions=["nautobot_network_provisioning.add_macaddress"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:macaddressentry_list",
                        name="CAM Tables",
                        weight=200,
                        permissions=["nautobot_network_provisioning.view_macaddressentry"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:arpentry_list",
                        name="ARP Entries",
                        weight=300,
                        permissions=["nautobot_network_provisioning.view_arpentry"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:macaddresshistory_list",
                        name="MAC History",
                        weight=400,
                        permissions=["nautobot_network_provisioning.view_macaddresshistory"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="System",
                weight=300,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_network_provisioning:controlsetting_list",
                        name="Controls",
                        weight=100,
                        permissions=["nautobot_network_provisioning.view_controlsetting"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_network_provisioning:controlsetting_add",
                                permissions=["nautobot_network_provisioning.add_controlsetting"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
