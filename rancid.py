#!/usr/bin/env python3 

from asyncio import run, gather
from file_operations import *
from gcp_operations import *

SETTINGS_FILE = 'settings.yaml'


async def main():

    try:
        if settings := await read_data_file(SETTINGS_FILE):
            file_format = settings.get('file_format', "toml")
        else:
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
            # Try to Authenticate via ADCs
            access_token = get_adc_token()
            _ = await get_project_ids(access_token)
            projects['default'] = [{'project_id': project_id, 'access_token': access_token} for project_id in _]
        except Exception as e:
            quit(e)
        print(projects)
        quit()

    calls = await read_data_file('calls.toml')

    tasks = []
    data_files = []
    for environment, projects in projects.items():
        for project in projects:
            try:
                if auth_file := project.get('auth_file'):
                    auth_key = f"{settings.get('key_dir', './')}/{auth_file}"
                    sa_key = read_service_account_key(auth_key)
                    project_id = sa_key.get('project_id')
                    access_token = sa_key.get('access_token')
                else:
                    auth_file = settings['environments'][environment].get('auth_file')
            except Exception as e:
                print(f"WARNING: {e}")
                continue
            for k, v in calls.items():
                urls = [f"/compute/v1/projects/{project_id}/{call}" for call in v.get('calls', [])]
                for url in urls:
                    print(project_id, url)
                    tasks.append(make_gcp_call(url, access_token, api_name='compute'))
                data_files.append(f'{project_id}/{k}s.{file_format}')

    _ = await gather(*tasks)
    _ = dict(zip(data_files, _))
    for file_name, data in _.items():
        sub_dir = file_name.split('/')[0]
        if not os.path.exists(sub_dir):
            os.makedirs(sub_dir)
        try:
            _ = await write_data_file(file_name, data)
        except Exception as e:
            print(f"WARNING: {e}")


if __name__ == "__main__":

    _ = run(main())
