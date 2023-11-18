#!/usr/bin/env python3 

import asyncio
import google.oauth2
import google.auth
import google.auth.transport.requests
from google.auth.transport.requests import Request

import json
import yaml
import os
import pathlib
import platform
from gcp_ip_addresses import make_gcp_call

SETTINGS_FILE = 'settings.yaml'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
CALLS = {
    'vpc_network': ("VPC Network", "global/networks"),
    'subnetwork': ("Subnetwork", "aggregated/subnetworks"),
    'firewall_rule': ("Firewall Rule", "global/firewalls"),
    'instance': ("Instance", "aggregated/instances"),
    'instance_group': ("Instance Group", "aggregated/instanceGroups"),
    'instance_group_manager': ("Instance Group Manager", "aggregated/instanceGroupManagers"),
    'instance_template': ("Instance Template", "aggregated/instanceTemplates"),
    'forwarding_rule': ("Regional Forwarding Rule", "aggregated/forwardingRules"),
    'global_forwarding_rule': ("Global Forwarding Rule", "global/forwardingRules"),
    'healthcheck': ("Health Check", "aggregated/healthChecks"),
    'cloud_router': ("Cloud Router", "aggregated/routers"),
    'static_route': ("Static Route", "global/routes"),
    'ssl_certificate': ("SSL Certificate", "aggregated/sslCertificates"),
    'security_policy': ("Cloud Armor Policy", "aggregated/securityPolicies"),
    'ssl_policy': ("SSL Policies", "aggregated/sslPolicies"),
    'vpn_tunnel': ("VPN Tunnel", "aggregated/vpnTunnels"),
    'cloud_vpn_gateway': ("Cloud VPN Gateway", "aggregated/vpnGateways"),
    'peer_vpn_gateway': ("Peer VPN Gateway", "global/externalVpnGateways"),
}


def read_yaml(yaml_file: str) -> dict:

    if path := pathlib.Path(yaml_file):
        if path.is_file():
            with open(yaml_file) as file:
                return yaml.load(file, Loader=yaml.FullLoader)


def read_service_account_key(file: str) -> str:

    # If running on Windows, change forward slashes to backslashes
    if platform.system().lower().startswith("win"):
        file = file.replace("/", "\\")
    #print(file)

    try:
        with open(file, 'r') as f:
            _ = json.load(f)
            project_id = _.get('project_id')
    except Exception as e:
        raise(e)

    try:
        credentials = google.oauth2.service_account.Credentials.from_service_account_file(file, scopes=SCOPES)
        _ = google.auth.transport.requests.Request()
        credentials.refresh(_)
        #access_token = credentials.token
        return {'project_id': project_id, 'access_token': credentials.token}
    except Exception as e:
        raise(e)


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


async def get_projects(access_token: str) -> list:

    try:
        return await make_gcp_call('/v1/projects', access_token, api_name='cloudresourcemanager')
    except Exception as e:
        raise e


async def get_project_ids(access_token: str) -> list:

    try:
        _ = await get_projects(access_token)
        return [project['projectId'] for project in _]
    except Exception as e:
        raise e


def write_to_bucket(bucket_name: str, file_name: str, data: str = ""):

    pass


async def main():

    try:
        if not (settings := read_yaml(SETTINGS_FILE)):
            quit(f"Could not read settings file '{SETTINGS_FILE}'")
    except Exception as e:
        quit(e)

    projects = {}
    if environments := settings.get('environments'):
        for environment, env_settings in environments.items():
            projects[environment] = []
            if auth_files := env_settings.get('auth_files'):
                for auth_file in auth_files:
                    projects[environment].append({
                        'auth_file': auth_file,
                    })
            else:
                projects = {}
    else:
        try:
            access_token = await get_adc_token()
            _ = await get_project_ids(access_token)
            projects['default'] = [{'project_id': project_id, 'access_token': access_token} for project_id in _]
        except Exception as e:
            quit(e)
        print(projects)
        quit()
    #print(projects)
    #quit()
    tasks = []
    json_files = []
    for environment, projects in projects.items():
        for project in projects:
            try:
                if auth_file := project.get('auth_file'):
                    auth_key = f"{settings.get('key_dir', './')}/{auth_file}"
                    _ = read_service_account_key(auth_key)
                    project_id = _.get('project_id')
                    access_token = _.get('access_token')
                else:
                    auth_file = settings['environments'][environment].get('auth_file')
            except Exception as e:
                print(f"WARNING: {e}")
                continue
            for short_name, info in CALLS.items():
                call = f'/compute/v1/projects/{project_id}/{info[1]}'
                tasks.append(make_gcp_call(call, access_token, api_name='compute'))
                json_files.append(f'{project_id}/{short_name}s.json')

    _ = await asyncio.gather(*tasks)
    _ = dict(zip(json_files, _))
    for file_name, data in _.items():
        sub_dir = file_name.split('/')[0]
        if not os.path.exists(sub_dir):
            os.makedirs(sub_dir)
        #print(dir, file_name)
        with open(file_name, 'w') as f:
            f.write(json.dumps(data))

    #print(_.items())


if __name__ == "__main__":

    _ = asyncio.run(main())
