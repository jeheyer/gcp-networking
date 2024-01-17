#!/usr/bin/env python3

from asyncio import run, gather
from collections import Counter
from file_operations import write_to_excel
from gcp_operations import get_projects, make_api_call, make_gcp_call, parse_item
from auth_operations import get_adc_token
from main import get_calls

CALLS = ('vpc_networks', 'firewall_rules', 'subnetworks', 'instance_nics', 'forwarding_rules', 'cloud_routers')
XLSX_FILE = "network_quotas.xlsx"


def sort_data(data: list, key: str, reverse: bool = True) -> list:

    return sorted(data, key=lambda _: _[key], reverse=reverse)


async def main():

    try:
        access_token = await get_adc_token()
    except Exception as e:
        quit(e)

    sheets = {
        'projects': {'description': "Project Counts"},
        'networks': {'description': "Network Counts"},
        'subnets': {'description': "Subnet Counts"},
        'cloud_nats': {'description': "Cloud NAT Counts"},
    }

    # Get all Projects
    projects = await get_projects(access_token)
    project_ids = [project['id'] for project in projects]

    # Form a dictionary of relevant API Calls
    _ = await get_calls()
    calls = {k: v.get('calls')[0] for k, v in _.items() if k in CALLS}

    # Get all network data
    network_data = {}
    for k, call in calls.items():
        # Perform API calls
        print(k, call)
        urls = [f"/compute/v1/projects/{project_id}/{call}" for project_id in project_ids]
        tasks = [make_gcp_call(url, access_token, api_name='compute') for url in urls]
        #tasks = [make_api_call(url, access_token) for url in urls]
        _ = await gather(*tasks)
        # Parse items and add to network_data
        items = []
        for row in _:
            if len(row) > 0:
                tasks = [parse_item(item) for item in row]
                _ = await gather(*tasks)
                items.extend(_)
        network_data[k] = items

    subnetworks = []
    fields = ('project_id', 'id', 'network_id', 'network_name', 'region')
    for subnetwork in network_data.pop('subnetworks'):
        _ = {field: subnetwork.get(field) for field in fields}
        _.update({
            'name':  subnetwork['name'],
            'usable_ips': (2 ** (32 - int(subnetwork['ipCidrRange'].split('/')[-1]))) - 4,
        })
        subnetworks.append(_)

    forwarding_rules = []
    fields = ('project_id', 'network_id', 'subnet_id', 'region')
    for forwarding_rule in network_data.pop('forwarding_rules'):
        _ = {field: forwarding_rule.get(field) for field in fields}
        _.update({
            'lb_scheme': forwarding_rule.get('loadBalancingScheme', "UNKNOWN"),   # Used to identify fwd rule type
        })
        forwarding_rules.append(_)

    routers = []
    fields = ('project_id', 'network_id', 'network_name', 'region')
    for router in network_data.pop('cloud_routers'):
        _ = {field: router.get(field) for field in fields}
        routers.append(_)

    firewalls = []
    fields = ('project_id', 'network_id', 'network_name')
    for firewall in network_data.pop('firewall_rules'):
        _ = {field: firewall.get(field) for field in fields}
        firewalls.append(_)

    instance_nics = []
    fields = ('project_id', 'network_id', 'network_name', 'subnet_id')
    for instance in network_data.pop('instance_nics'):
        for nic in instance.get('networkInterfaces', []):
            nic = await parse_item(nic)
            _ = {field: nic.get(field) for field in fields}
            _.update({
                'name': instance['name'] + "-" + nic['name'],
                'region': instance['region'],
                'zone': instance.get('zone'),
            })
            instance_nics.append(_)

    networks = []
    for network in network_data.pop('vpc_networks'):
        network_id = network['id']
        counts = {
            'peerings': network.get('peerings', []),
            'instances': [_ for _ in instance_nics if _.get('network_id') == network_id],
            'forwarding_rules': [_ for _ in forwarding_rules if _.get('network_id') == network_id],
            'firewall_rules': [_ for _ in firewalls if _.get('network_id') == network_id],
            'routers':  [_ for _ in routers if _.get('network_id') == network_id],
        }
        counts.update({
            'application': [_ for _ in counts['forwarding_rules'] if _['lb_scheme'] == "INTERNAL_MANAGED"],
            'passthrough': [_ for _ in counts['forwarding_rules'] if _['lb_scheme'] == "INTERNAL"],
        })
        _ = {field: network.get(field) for field in ('project_id', 'name', 'id')}
        _.update({
            'num_subnets': len(network.get('subnetworks', [])),
            'num_peerings': len(counts['peerings']),
            'num_routers': len(counts['routers']),
            'num_instances': len(counts['instances']),
            'num_firewall_rules': len(counts['firewall_rules']),
            'num_forwarding_rules': len(counts['forwarding_rules']),
            'application': len(counts['application']),
            'passthrough': len(counts['passthrough']),
        })
        networks.append(_)
    sheets['networks']['data'] = sort_data(networks, 'num_instances')

    subnet_counts = []
    for subnet in subnetworks:
        subnet_id = subnet["id"]
        counts = {
            'instances': [_ for _ in instance_nics if _.get('subnet_id') == subnet_id],
            'forwarding_rules': [_ for _ in forwarding_rules if _.get('subnet_id') == subnet_id],
        }
        active_ips = len(counts['instances']) + len(counts['forwarding_rules'])
        subnet_counts.append({
            'project_id': subnet['project_id'],
            'network_name': subnet['network_name'],
            'region': subnet['region'],
            'subnet_name': subnet['name'],
            'num_instances': len(counts['instances']),
            'num_forwarding_rules': len(counts['forwarding_rules']),
            'utilization': round(active_ips / subnet['usable_ips'] * 100)
        })
    sheets['subnets']['data'] = sort_data(subnet_counts, 'num_instances')

    project_counts = []
    for project in projects:
        project_id = project['id']
        counts = {
            'networks': [_ for _ in networks if _['project_id'] == project_id],
            'firewalls': [_ for _ in firewalls if _['project_id'] == project_id],
            'routers': [_ for _ in routers if _['project_id'] == project_id],
        }
        project_counts.append({
            'project_id': project_id,
            'project_number': project.get('number'),
            'project_status': project.get('status', "UNKNOWN"),
            'num_networks': len(counts['networks']),
            'num_firewalls': len(counts['firewalls']),
            'num_routers': len(counts['routers']),
        })
    sheets['projects']['data'] = sort_data(project_counts, 'num_networks')

    cloud_nats = []
    for network in networks:
        _ = Counter([nic['region'] for nic in instance_nics if nic['network_id'] == network['id']])
        for region, instance_count in _.items():
            cloud_nats.append({
                'network_project_id': network['project_id'],
                'network_name': network['name'],
                'region': region,
                'num_instances': instance_count,
            })
    sheets['cloud_nats']['data'] = sort_data(cloud_nats, 'num_instances')

    # Create and save the Excel workbook
    _ = await write_to_excel(sheets, XLSX_FILE)

if __name__ == "__main__":

    run(main())
