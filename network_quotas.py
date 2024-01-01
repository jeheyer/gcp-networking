#!/usr/bin/env python3

from asyncio import run, gather
from collections import Counter
from file_operations import read_data_file, write_data_file, write_to_excel
from gcp_operations import get_adc_token, get_projects, get_project_ids, make_gcp_call, parse_results


async def main():

    try:
        access_token = get_adc_token()
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
        #'subnetworks': "aggregated/subnetworks",
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
            if len(row['items']) > 0:
                items.extend(row['items'])
        raw_data.update({k: items})

    forwarding_rules = []
    for forwarding_rule in raw_data.pop('forwarding_rules'):
        if subnetwork := forwarding_rule.get('subnetwork'):
            subnetwork = subnetwork.replace('https://www.googleapis.com/compute/v1/', "")
            forwarding_rule.update({'subnetwork': subnetwork})
        forwarding_rules.append(forwarding_rule)

    routers = []
    for router in raw_data.pop('routers'):
        self_link = router['selfLink']
        routers.append({
            'project_id': self_link.split('/')[-5],
            'name': router['name'],
            'region': self_link.split('/')[-3],
            'network': router['network'],
        })

    firewalls = []
    for firewall in raw_data.pop('firewalls'):
        print(firewall)
        self_link = firewall['selfLink']
        firewalls.append({
            'project_id': self_link.split('/')[-4],
            'name': firewall['name'],
            'network': firewall['network'],
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
    subnets = []
    for network in raw_data.pop('networks'):
        self_link = network['selfLink']
        network_name = self_link.split("/")[-1]
        network_project_id = self_link.split("/")[-4]
        network_id = f"projects/{network_project_id}/global/networks/{network_name}"

        subnetworks = network.get('subnetworks', [])
        for subnetwork in subnetworks:
            subnets.append({
                'network_project_id': network_project_id,
                'network_name': network_name,
                'region': subnetwork.split('/')[-3],
                'name': subnetwork.split('/')[-1],
                'subnetwork': subnetwork.replace('https://www.googleapis.com/compute/v1/', "")
            })
        counts = {
            'peerings': network.get('peerings', []),
            'instances': [_ for _ in instance_nics if _.get('network') == network_id],
            'forwarding_rules': [_ for _ in forwarding_rules if _.get('network') == self_link],
        }
        networks.append({
            'project_id': network_project_id,
            'name': network_name,
            'network': network_id,
            'num_subnets': len(subnetworks),
            'num_peerings': len(counts['peerings']),
            'num_instances': len(counts['instances']),
            'num_forwarding_rules': len(counts['forwarding_rules']),
        })
    sheets['networks']['data'] = networks

    subnet_counts = []
    for subnet in subnets:
        counts = {
            'instances': [_ for _ in instance_nics if subnet['subnetwork'] == _.get('subnetwork')],
            'forwarding_rules': [_ for _ in forwarding_rules if subnet['subnetwork'] == _.get('subnetwork')],
        }
        subnet_counts.append({
            'network_project_id': subnet['network_project_id'],
            'network_name': subnet['network_name'],
            'region': subnet['region'],
            'subnet_name': subnet['name'],
            'num_instances': len(counts['instances']),
            'num_forwarding_rules': len(counts['forwarding_rules']),
        })
    sheets['subnets']['data'] = subnet_counts

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
    sheets['projects']['data'] = projects

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
    sheets['cloud_nats']['data'] = cloud_nats

    # Create and save the Excel workbook
    _ = await write_to_excel(sheets, "network_quotas.xlsx")

if __name__ == "__main__":

    run(main())
