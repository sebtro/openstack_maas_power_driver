# 2022 Sebastian Trojanowski

from importlib import import_module, invalidate_caches
import urllib, sys, json

from provisioningserver.drivers import (
    IP_EXTRACTOR_PATTERNS,
    make_ip_extractor,
    make_setting_field,
    SETTING_SCOPE,
)
from provisioningserver.drivers.power import (
    is_power_parameter_set,
    PowerAuthError,
    PowerConnError,
    PowerDriver,
    PowerError,
    PowerFatalError,
    PowerSettingError,
    PowerToolError,
)

from provisioningserver.events import EVENT_TYPES, send_node_event
from provisioningserver.logger import get_maas_logger

import openstack
maaslog = get_maas_logger("drivers.power.openstackdrv")

#openstack.enable_logging(debug=False, path='openstack.log', stream=sys.stdout)

class OpenStackDriver(PowerDriver):
    name = "OpenStack"
    chassis = False
    can_probe = False
    can_set_boot_order = False
    description = "OpenStack Driver"
    settings = [
        make_setting_field("server_uuid", "Server UUID", required=True),
        make_setting_field("os_projectname", "Project name", required=True),
        make_setting_field("os_project_domain", "Project domain", required=True),
        make_setting_field("os_region", "Region name", required=True),
        make_setting_field("os_user_domain", "User domain name", required=True),
        make_setting_field("os_username", "Username", required=True),
        make_setting_field("os_password","Password",field_type="password",required=True),
        make_setting_field("os_authurl", "Auth URL", required=True),
    ]
    ip_extractor = make_ip_extractor("os_authurl",IP_EXTRACTOR_PATTERNS.URL)

    def power(self,power_change,os_authurl,os_projectname,os_username,os_password,os_region,os_user_domain,os_project_domain,server_uuid, **extra):
        conn = openstack.connect(
            auth_url=os_authurl,
            project_name=os_projectname,
            username=os_username,
            password=os_password,
            region_name=os_region,
            user_domain_name=os_user_domain,
            project_domain_name=os_project_domain,
        )
        maaslog.info("url: %s ." % os_authurl)
        if power_change=="on":
            conn.compute.start_server(server_uuid)
            server_status=conn.compute.get_server(server_uuid)
            while (server_status.status!="ACTIVE"):    
                server_status=conn.compute.get_server(server_uuid)
                
        if power_change=="off":
            server_status=conn.compute.get_server(server_uuid)
            conn.compute.stop_server(server_uuid)
            while (server_status.status!="SHUTOFF"):
                server_status=conn.compute.get_server(server_uuid)

        if power_change=="status":
            server_status=conn.compute.get_server(server_uuid)
            if server_status.status == "ACTIVE":
                return "on"
            elif server_status.status == "SHUTOFF":
                return "off"
            else:
                raise PowerActionError(
                "Openstack Power Driver retrieved unknown power state: %r"
                % power_state
            )

    def detect_missing_packages(self):
        # TBD python3-openstacksdk
        return []

    def power_query(self,system_id,context):
        return self.power("status",**context)
    def power_on(self,system_id,context):
        self.power("on",**context)
    def power_off(self,system_id,context):
        self.power("off",**context)
        
