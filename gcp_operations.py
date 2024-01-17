from aiohttp import ClientSession
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
VERIFY_SSL = True

"""
def get_adc_token():

    try:
        credentials, project_id = google.auth.default(scopes=SCOPES, quota_project_id=None)
        _ = google.auth.transport.requests.Request()
        credentials.refresh(_)
        return credentials.token
    except Exception as e:
        raise e


def read_service_account_key(file: str) -> str:

    # If running on Windows, change forward slashes to backslashes
    if platform.system().lower().startswith("win"):
        file = file.replace("/", "\\")

    try:
        with open(file, 'r') as f:
            _ = json.load(f)
            project_id = _.get('project_id')
    except Exception as e:
        raise e

    try:
        credentials = google.oauth2.service_account.Credentials.from_service_account_file(file, scopes=SCOPES)
        _ = google.auth.transport.requests.Request()
        credentials.refresh(_)
        return {'project_id': project_id, 'access_token': credentials.token}
    except Exception as e:
        raise e
"""


async def make_gcp_call(call: str, access_token: str, api_name: str) -> dict:

    call = call[1:] if call.startswith("/") else call
    url = f"https://{api_name}.googleapis.com/{call}"
    if api_name in ['compute', 'sqladmin']:
        if 'aggregated' in call or 'global' in call:
            key = 'items'
        else:
            key = 'result'
    else:
        key = url.split("/")[-1]

    results = []
    call_id = None
    try:
        headers = {'Authorization': f"Bearer {access_token}"}
        params = {}
        async with ClientSession(raise_for_status=True) as session:
            while True:
                async with session.get(url, headers=headers, params=params) as response:
                    if int(response.status) == 200:
                        json_data = await response.json()
                        call_id = json_data.get('id')
                        if 'aggregated/' in url:
                            if key == 'items':
                                items = json_data.get(key, {})
                                for k, v in items.items():
                                    results.extend(v.get(url.split("/")[-1], []))
                        else:
                            if key == 'result':
                                items = json_data.get(key)
                                results.append(items)
                            else:
                                items = json_data.get(key, [])
                                results.extend(items)
                        if page_token := json_data.get('nextPageToken'):
                            params.update({'pageToken': page_token})
                        else:
                            break
                    else:
                        raise response
    except Exception as e:
        await session.close()

    return results


async def get_projects(access_token: str, sort_by: str = None) -> list:

    projects = []
    fields = {'name': "name", 'id': "projectId", 'number': "projectNumber", 'created': "createTime",
              'status': "lifecycleState"}
    try:
        _ = await make_api_call('https://cloudresourcemanager.googleapis.com/v1/projects', access_token)
        if sort_by in fields.values():
            # Sort by a field defined in the API
            _ = sorted(_, key=lambda x: x.get(sort_by), reverse=False)
        for project in _:
            projects.append({k: project.get(v, "UNKNOWN") for k, v in fields.items()})
        if sort_by in fields.keys():
            # Sort by a field defined by us
            projects = sorted(projects, key=lambda x: x.get(sort_by), reverse=False)

    except Exception as e:
        raise e

    return projects


async def get_project_ids(access_token: str, projects: list = None) -> list:

    try:
        projects = projects if projects else await get_projects(access_token)
        return [project['id'] for project in projects]
    except Exception as e:
        raise e


def convert_gcp_timestamp(gcp_timestamp: str = None) -> str:

    time_stamp = 0

    if gcp_timestamp:
        try:
            date_time = f"{gcp_timestamp[:10]} {gcp_timestamp[11:19]}"
            time_stamp = datetime.datetime.timestamp(datetime.datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            raise e

    return int(time_stamp)


def parse_results(items: list, parse_function: str) -> list:

    project_id = 'unknown'
    #if results_id := results.get('id'):
    #    project_id = results_id.split('/')[1]

    parsed_items = []

    for item in items:
        if region := item.get('region'):
            region = region.split('/')[-1]
        else:
            region = "global"
        _ = {
            'project_id': project_id,
            'name': item.get('name'),
            'description': item.get('description')[0:31] if 'description' in item else "",
            'region': region,
        }
        if network := item.get('network'):
            network_name = network.split('/')[-1]
            network_project_id = network.split('/')[-4]
            network_id = f"{network_project_id}/{network_name}"
        else:
            network_id = "n/a"
        if subnetwork := item.get('subnetwork'):
            subnet_name = subnetwork.split('/')[-1]
            subnet_id = f"{network_project_id}/{region}/{subnet_name}"
        else:
            subnet_id = "n/a"
        _.update({
            'network_id': network_id,
            'subnet_id': subnet_id,
        })
        _.update({'creation_timestamp': item.get('creationTimestamp')}) # #convert_gcp_timestamp(item.get('creationTimestamp'))

        if parse_function == "parse_networks":
            _ = parse_network(_, item)
        if parse_function == "parse_firewall_rules":
            _ = parse_firewall_rule(_, item)
        if parse_function == "parse_subnets":
            _ = parse_subnet(_, item)
        if parse_function == "parse_instance_nics":
            _ = parse_instance_nics(_, item)
        if parse_function == "parse_forwarding_rules":
            _ = parse_forwarding_rules(_, item)
        if parse_function == "parse_global_forwarding_rules":
            _ = parse_forwarding_rules(_, item)
        if parse_function == "parse_cloud_vpn_gateways":
            _ = parse_cloud_vpn_gateways(_, item)
        if parse_function == "parse_peer_vpn_gateways":
            _ = parse_peer_vpn_gateways(_, item)
        if parse_function == "parse_vpn_tunnels":
            _ = parse_vpn_tunnels(_, item)
        if parse_function == "parse_cloud_routers":
            _ = parse_cloud_routers(_, item)

        if type(_) is list:
            parsed_items.extend(_)
        else:
            parsed_items.append(_)

    return parsed_items


def parse_network(item: dict, raw_data: dict) -> list:

    if routing_config := raw_data.get('routingConfig'):
        item.update({
            'routing_mode': routing_config.get('routingMode', "UNKNOWN"),
        })
    item.update({
        'num_subnets': len(raw_data.get('subnetworks', [])),
        'mtu': raw_data.get('mtu'),
        'auto_create_subnets': raw_data.get('autoCreateSubnetworks', False)
    })
    del item['network_id']
    del item['region']
    del item['subnet_id']

    return item


def parse_subnet(item: dict, raw_data: dict) -> list:

    item.update({
        'cidr_range': raw_data.get('ipCidrRange'),
    })
    del item['subnet_id']

    return item


def parse_firewall_rule(item: dict, raw_data: dict) -> list:

    del item['region']
    del item['subnet_id']

    return item


def parse_forwarding_rules(item: dict, raw_data: dict) -> list:

    item.update({
        'ip_address': raw_data.get('IPAddress'),
        'lb_scheme': raw_data.get('loadBalancingScheme', "UNKNOWN"),
    })
    if port_range := raw_data.get('portRange'):
        ports = str(port_range.split("-"))
    else:
        ports = raw_data.get('ports', "all")
    item.update({'ports': ports})

    return item


def parse_instance_nics(item: dict, raw_data: dict) -> list:

    # Information about the instance
    zone = raw_data.get('zone', "unknown-0").split('/')[-1]
    region = zone[:-2]
    machine_type = raw_data.get('machineType', "unknown/unknown").split('/')[-1]
    ip_forwarding = raw_data.get('canIpForward', False)
    status = raw_data.get('status', "UNKNOWN")

    instance_nics = []
    for index, nic in enumerate(raw_data.get('networkInterfaces', [])):
        ip_address = nic.get('networkIP')
        network_id = "n/a"
        if network := nic.get('network'):
            network_name = network.split("/")[-1]
            network_project_id = network.split("/")[-4]
            network_id = f"{network_project_id}/{network_name}"
            subnet_id = "n/a"
            if subnetwork := nic.get('subnetwork'):
                subnet_name = subnetwork.split('/')[-1]
                subnet_region = subnetwork.split('/')[-3]
                subnet_id = f"{network_project_id}/{subnet_region}/{subnet_name}"

        # Also check if the instance has any active NAT IP addresses
        external_ip_address = None
        if access_configs := nic.get('accessConfigs'):
            for access_config in access_configs:
                external_ip_address = access_config.get('natIP')

        instance_nic = {
            'name': f"{item.get('name')}-nic{index}",
            'project_id': item.get('project_id', "unknown"),
            'network_id': network_id,
            'subnet_id': subnet_id,
            'ip_address': ip_address,
            'external_ip_address': external_ip_address,
            'region': region,
            'zone': zone,
            'machine_type': machine_type,
            'ip_forwarding': ip_forwarding,
            'status': status,
        }
        instance_nics.append(instance_nic)

    return instance_nics


def parse_cloud_vpn_gateways(item: dict, raw_data: dict) -> dict:

    vpn_ips = [ vpn_interface['ipAddress'] for vpn_interface in raw_data.get('vpnInterfaces', [])]
    item.update({
        'vpn_ips': vpn_ips,
    })
    del item['subnet_id']

    return item


def parse_peer_vpn_gateways(item: dict, raw_data: dict) -> dict:

    interface_ips = [interface['ipAddress'] for interface in raw_data.get('interfaces', [])]
    item.update({
        'redundancy_type': raw_data.get('redundancyType', "UNKNOWN"),
        'interface_ips': interface_ips,
    })
    del item['network_id']
    del item['subnet_id']
    del item['region']

    return item


def parse_vpn_tunnels(item: dict, raw_data: dict) -> dict:

    item.update({
        'vpn_gateway': raw_data['vpnGateway'].split('/')[-1] if 'vpnGateway' in raw_data else None,
        'interface': raw_data.get('vpnGatewayInterface'),
        'peer_gateway': raw_data['peerExternalGateway'].split('/')[-1] if 'peerExternalGateway' in raw_data else None,
        'peer_ip': raw_data.get('peerIp'),
        'ike_version': raw_data.get('ikeVersion', 0),
        'status': raw_data.get('status'),
        'detailed_status': raw_data.get('detailedStatus'),
    })
    del item['network_id']
    del item['subnet_id']

    return item


def parse_cloud_routers(item: dict, raw_data: dict) -> dict:

    item.update({
        'interfaces': raw_data.get('interfaces', []),
    })
    del item['subnet_id']

    return item


async def parse_item(item: dict) -> dict:

    if zone := item.get('zone'):
        zone = zone.split('/')[-1]
        region = zone[:-2]
    else:
        region = item.get('region', "/global").split('/')[-1]

    if self_link := item.get('selfLink'):
        id = self_link.replace('https://www.googleapis.com/compute/v1/', "")
        project_id = self_link.split('/')[-4 if region == 'global' else -5]
        item.update({
            #'self_link': self_link,
            'id': id,
            'project_id': project_id,
            'region': region,
        })
        del item['selfLink']  # No longer need self link because we have the ID
    else:
        id = ""

    if id.endswith('/networks'):
        item.update({'network': id})
    if id.endswith('/subnetworks'):
        item.update({'subnetwork': id})

    if network := item.get('network'):
        network_id = network.replace('https://www.googleapis.com/compute/v1/', "")
        network_name = network.split('/')[-1]
        item.update({'network_id': network_id, 'network_name': network_name})
    if subnetwork := item.get('subnetwork'):
        subnet_id = subnetwork.replace('https://www.googleapis.com/compute/v1/', "")
        subnet_name = subnetwork.split('/')[-1]
        item.update({'subnet_id': subnet_id, 'subnet_name': subnet_name})
    if zone:
        item.update({'zone': zone})

    return item


async def make_api_call(url: str, access_token: str) -> list:

    if url.startswith('http:') or url.startswith('https:'):
        # Urls is fully defined, just need to find API name
        _ = url[7:] if url.startswith('http:') else url[8:]
        api_name = _.split('.')[0]
    elif 'googleapis.com' in url:
        # Url is missing http/https at the beginning
        api_name = url.split('.')[0]
        url = f"https://{url}"
    elif '.' in url:
        raise f"Unhandled URL: {url}"
    else:
        # Url is something like /compute/v1/projects/{PROJECT_ID}...
        url = url[1:] if url.startswith("/") else url
        api_name = url.split('/')[0]
        url = f"https://{api_name}.googleapis.com/{url}"

    if api_name in ['compute', 'sqladmin']:
        items_key = 'items'
    else:
        items_key = url.split("/")[-1]

    try:
        headers = {'Authorization': f"Bearer {access_token}"}
        params = {}  # Query string parameters to include in the request
        async with ClientSession(raise_for_status=True) as session:
            results = []
            while True:
                async with session.get(url, headers=headers, params=params, verify_ssl=VERIFY_SSL) as response:
                    if int(response.status) == 200:
                        json_data = await response.json()
                        if items := json_data.get(items_key):
                            if 'aggregated/' in url:
                                # With aggregated results, we have to walk each region to get the items
                                for k, v in items.items():
                                    _ = url.split("/")[-1]
                                    items = v.get(_, [])
                            results.extend(items)
                        else:
                            if json_data.get('name'):
                                results.append(json_data)
                        # If more than 500 results, use page token for next page and keep the party going
                        if next_page_token := json_data.get('nextPageToken'):
                            params.update({'pageToken': next_page_token})
                        else:
                            break
                    else:
                        break  # non-200 usually means lack of permissions; just skip it
    except Exception as e:
        await session.close()    # Something went wrong when opening the session; don't leave it hanging

    return results

