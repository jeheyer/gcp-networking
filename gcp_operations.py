import platform
import json
import google.oauth2
import google.auth
import google.auth.transport.requests
import datetime
from aiohttp import ClientSession

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']


async def get_adc_token():

    try:
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        credentials, project_id = google.auth.default(scopes=scopes, quota_project_id=None)
        _ = google.auth.transport.requests.Request()
        credentials.refresh(_)
        access_token = credentials.token
        return access_token
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


async def make_gcp_call(call: str, access_token: str, api_name: str) -> dict:

    results = {'id': None, 'items': []}

    call = call[1:] if call.startswith("/") else call
    url = f"https://{api_name}.googleapis.com/{call}"
    if api_name in ['compute', 'sqladmin']:
        if 'aggregated' in call or 'global' in call:
            key = 'items'
        else:
            key = 'result' #bool(match(r'aggregated|global', call)) else 'result'
        #print(api_name, call, key)
    else:
        key = url.split("/")[-1]

    #print(url)
    try:
        headers = {'Authorization': f"Bearer {access_token}"}
        params = {}
        async with ClientSession(raise_for_status=True) as session:
            while True:
                async with session.get(url, headers=headers, params=params) as response:
                    if int(response.status) == 200:
                        json_data = await response.json()
                        results['id'] = json_data.get('id')
                        if 'aggregated/' in url:
                            if key == 'items':
                                items = json_data.get(key, {})
                                for k, v in items.items():
                                     results['items'].extend(v.get(url.split("/")[-1], []))
                        else:
                            #print(key)
                            if key == 'result':
                                items = json_data.get(key)
                                results['items'].append(items)
                            else:
                                items = json_data.get(key, [])
                                results['items'].extend(items)
                        if page_token := json.get('nextPageToken'):
                            params.update({'pageToken': page_token})
                        else:
                            break
                    else:
                        raise response
    except Exception as e:
        await session.close()

    return results


async def get_projects(access_token: str) -> list:

    projects = []
    try:
        _ = await make_gcp_call('/v1/projects', access_token, api_name='cloudresourcemanager')
        _ = sorted(_['items'], key=lambda x: x.get('name'), reverse=False)
        for project in _:
            projects.append({
                'name': project.get('name', "UNKNOWN"),
                'id': project.get('projectId', "UNKNOWN"),
                'number': project.get('projectNumber', "UNKNOWN"),
                'created': project.get('createTime', "UNKNOWN"),
                'state': project.get('lifecycleState', "UNKNOWN"),
            })

    except Exception as e:
        raise e

    return projects


async def get_project_ids(access_token: str, projects: list = None) -> list:

    try:
        _ = projects if projects else await get_projects(access_token)
        return [project['id'] for project in _]
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


def parse_results(results: dict, parse_function: str) -> list:

    project_id = 'unknown'
    if results_id := results.get('id'):
        project_id = results_id.split('/')[1]

    parsed_items = []

    for item in results.get('items'):
        if region := item.get('region'):
            region = region.split('/')[-1]
        else:
            region = "global"
        _ = {
            'project_id': project_id,
            'name': item.get('name'),
            'description': item.get('description')[0:63] if 'description' in item else "",
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
