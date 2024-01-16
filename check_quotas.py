#!/usr/bin/env python3

from asyncio import run, gather
from collections import Counter
from file_operations import read_data_file, write_data_file, write_to_excel
from gcp_operations import get_projects, get_project_ids, make_gcp_call, parse_results
from auth_operations import get_adc_token


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

    project_ids = await get_project_ids(access_token)

    # Define API calls related to getting network quota / sizing info
    calls = {
        'networks': "global/networks",
        'firewalls': "global/firewalls",
        'subnetworks': "aggregated/subnetworks",
        'instances': "aggregated/instances",
        'forwarding_rules': "aggregated/forwardingRules",
        'routers': "aggregated/routers",
    }

    raw_data = {}
    for k, call in calls.items():
        tasks = []
        # For each project ID, get network data
        for project_id in project_ids:
            url = f"/compute/v1/projects/{project_id}/{call}"
            tasks.append(make_gcp_call(url, access_token, api_name='compute'))
        _ = await gather(*tasks)
        items = []
        for row in _:
            if len(row) > 0:
                items.extend(row)
        raw_data.update({k: items})

    subnetworks = []
    for subnetwork in raw_data.pop('subnetworks'):
        self_link = subnetwork['selfLink']
        network = subnetwork['network'].replace('https://www.googleapis.com/compute/v1/', "")
        subnetworks.append({
            'project_id': self_link.split('/')[-5],
            'region': subnetwork['region'].split('/')[-1],
            'network': network,
            'name':  subnetwork['name'],
            'usable_ips': (2 ** (32 - int(subnetwork['ipCidrRange'].split('/')[-1]))) - 4,
        })

    forwarding_rules = []
    for forwarding_rule in raw_data.pop('forwarding_rules'):
        if subnetwork := forwarding_rule.get('subnetwork'):
            subnetwork = subnetwork.replace('https://www.googleapis.com/compute/v1/', "")
            self_link = forwarding_rule['selfLink']
            forwarding_rules.append({
                'project_id': self_link.split('/')[-5],
                'network': forwarding_rule['network'].replace('https://www.googleapis.com/compute/v1/', ""),
                'subnetwork': subnetwork,
                'region': self_link.split('/')[-3],
                'lb_scheme': forwarding_rule.get('loadBalancingScheme', "UNKNOWN"),
            })

    routers = []
    for router in raw_data.pop('routers'):
        self_link = router['selfLink']
        network = router['network'].replace('https://www.googleapis.com/compute/v1/', "")
        routers.append({
            'project_id': self_link.split('/')[-5],
            'region': self_link.split('/')[-3],
            'network': network,
        })

    firewalls = []
    for firewall in raw_data.pop('firewalls'):
        self_link = firewall['selfLink']
        network = firewall['network'].replace('https://www.googleapis.com/compute/v1/', "")
        firewalls.append({
            'project_id': self_link.split('/')[-4],
            'network': network,
        })

    instance_nics = []
    for instance in raw_data.pop('instances'):
        for nic in instance.get('networkInterfaces', []):
            if network := nic.get('network'):
                network = network.replace('https://www.googleapis.com/compute/v1/', "")
                if subnetwork := nic.get('subnetwork'):
                    subnetwork = subnetwork.replace('https://www.googleapis.com/compute/v1/', "")
                instance_nics.append({
                    'name': instance['name'] + "-" + nic['name'],
                    'network': network,
                    'region': subnetwork.split('/')[-3],
                    'subnetwork': subnetwork,
                    'zone': instance.get('zone'),
                })

    networks = []
    for network in raw_data.pop('networks'):
        self_link = network['selfLink']
        network_name = self_link.split("/")[-1]
        network_project_id = self_link.split("/")[-4]
        network_id = f"projects/{network_project_id}/global/networks/{network_name}"
        counts = {
            'peerings': network.get('peerings', []),
            'instances': [_ for _ in instance_nics if _.get('network') == network_id],
            'forwarding_rules': [_ for _ in forwarding_rules if _.get('network') == network_id],
            'firewall_rules': [_ for _ in firewalls if _.get('network') == network_id],
            'routers':  [_ for _ in routers if _.get('network') == network_id],
        }
        counts.update({
            'application': [_ for _ in counts['forwarding_rules'] if _['lb_scheme'] == "INTERNAL_MANAGED"],
            'passthrough': [_ for _ in counts['forwarding_rules'] if _['lb_scheme'] == "INTERNAL"],
        })
        networks.append({
            'project_id': network_project_id,
            'name': network_name,
            'network': network_id,
            'num_subnets': len(network.get('subnetworks', [])),
            'num_peerings': len(counts['peerings']),
            'num_routers': len(counts['routers']),
            'num_instances': len(counts['instances']),
            'num_firewall_rules': len(counts['firewall_rules']),
            'num_forwarding_rules': len(counts['forwarding_rules']),
            'application': len(counts['application']),
            'passthrough': len(counts['passthrough']),
        })
    sheets['networks']['data'] = sort_data(networks, 'num_instances')

    subnet_counts = []
    for subnet in subnetworks:
        subnet_id = f"projects/{subnet['project_id']}/regions/{subnet['region']}/subnetworks/{subnet['name']}"
        counts = {
            'instances': [_ for _ in instance_nics if _.get('subnetwork') == subnet_id],
            'forwarding_rules': [_ for _ in forwarding_rules if _.get('subnetwork') == subnet_id],
        }
        active_ips = len(counts['instances']) + len(counts['forwarding_rules'])
        subnet_counts.append({
            'project_id': subnet['project_id'],
            'network': subnet['network'].split('/')[-1],
            'region': subnet['region'],
            'subnet_name': subnet['name'],
            'num_instances': len(counts['instances']),
            'num_forwarding_rules': len(counts['forwarding_rules']),
            'utilization': round(active_ips / subnet['usable_ips'] * 100)
        })
    sheets['subnets']['data'] = sort_data(subnet_counts, 'num_instances')

    projects = []
    for project_id in project_ids:
        counts = {
            'networks': [_ for _ in networks if _['project_id'] == project_id],
            'firewalls': [_ for _ in firewalls if _['project_id'] == project_id],
            'routers': [_ for _ in routers if _['project_id'] == project_id],
        }
        projects.append({
            'project_id': project_id,
            'num_networks': len(counts['networks']),
            'num_firewalls': len(counts['firewalls']),
            'num_routers': len(counts['routers']),
        })
    sheets['projects']['data'] = sort_data(projects, 'num_networks')

    cloud_nats = []
    for network in networks:
        _ = Counter([nic['region'] for nic in instance_nics if nic['network'] == network['network']])
        for region, instance_count in _.items():
            cloud_nats.append({
                'network_project_id': network['project_id'],
                'network_name': network['name'],
                'region': region,
                'num_instances': instance_count,
            })
    sheets['cloud_nats']['data'] = sort_data(cloud_nats, 'num_instances')

    # Create and save the Excel workbook
    _ = await write_to_excel(sheets, "network_quotas.xlsx")

if __name__ == "__main__":

    run(main())
