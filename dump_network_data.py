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
        sheets.update({k: {'description': v.get('description'), 'data': []}})

    project_ids = await get_project_ids(access_token, projects)
    for k, v in calls.items():
        tasks = []
        # For each project ID, get network data
        for project_id in project_ids:
            call = f"/compute/v1/projects/{project_id}/{v.get('call')}"
            print(call)
            tasks.append(make_gcp_call(call, access_token, api_name='compute'))
            #print(short_name, project_id)
        _ = await gather(*tasks)
        #pprint.pprint(_)
        #quit()
        data = []
        for items in _:
            for item in items:
                #print(item)
                #quit()
                row = {
                    'name': item.get('name'),
                    'project_id': item.get('network'),
                    'region': item.get('region'),
                }
                data.append(row)
        #network_data = [row if len(row) > 0 else None for row in _]
        #network_data[short_name]
        #print(network_data[short_name])
        #if  != 'projects':
        sheets.update({k: {'data': data}})
    #for k, v in network_data.items():
    #    print(k, v[0] if len(v) > 0 else None)
    #quit()
    #for short_name in CALLS.items():
    #    sheets.update({f"{short_name}s": network_data[short_name]}) = dict(zip(SHEETS, network_data))

    #for k, v in network_data.items():
    #    print(k, v[0] if len(v) > 0 else None)
    #quit()
    for k, v in sheets.items():
        print(k, v)

    sheet_data = {}
    for k, v in sheets.items():
        sheet_description = v.get('description', "Uknown")
        sheet_data = v.get('data', [])

    _ = await write_to_excel(sheets)
    #print(_.items())


if __name__ == "__main__":

    _ = run(main())
