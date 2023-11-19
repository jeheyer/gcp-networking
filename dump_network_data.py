#!/usr/bin/env python3

from asyncio import run, gather
from file_operations import *
from gcp_operations import *


async def main():

    try:
        access_token = await get_adc_token()
    except Exception as e:
        quit(e)

    # Get projects and create first sheet
    projects = await get_projects(access_token)
    sheets = {'projects': {'description': "Projects", 'data': projects}}

    # Add the other sheets
    calls = await read_data_file('calls.toml')
    for k, v in calls.items():
        new_sheet = {k: {'description': v.get('description'), 'data': []}}
        sheets.update(new_sheet)

    project_ids = await get_project_ids(access_token, projects)
    for k, v in calls.items():
        tasks = []
        # For each project ID, get network data
        for project_id in project_ids:
            if v.get('parse_function'):
                if calls := v.get('calls'):
                    for call in calls:
                        url = f"/compute/v1/projects/{project_id}/{call}"
                        tasks.append(make_gcp_call(url, access_token, api_name='compute'))
        _ = await gather(*tasks)

        data = []
        for results in _:
            parse_function = v.get('parse_function')
            items = parse_results(results, parse_function)
            data.extend(items)
        new_sheet = {k: {'description': v.get('description'), 'data': data}}
        sheets.update(new_sheet)

    _ = await write_to_excel(sheets)

if __name__ == "__main__":

    _ = run(main())
