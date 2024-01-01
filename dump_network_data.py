#!/usr/bin/env python3

from asyncio import run, gather
from file_operations import read_data_file, write_to_excel
from gcp_operations import get_adc_token, get_projects, make_gcp_call, parse_results


async def main():

    try:
        access_token = get_adc_token()
    except Exception as e:
        quit(e)

    # Get projects and create first sheet
    projects = await get_projects(access_token)
    sheets = {'projects': {'description': "Projects", 'data': projects}}
    project_ids = [project['id'] for project in projects]

    # Add the other sheets
    calls = await read_data_file('calls.toml')

    for k, v in calls.items():
        tasks = []
        # For each project ID, get network data
        for project_id in project_ids:
            if parse_function := v.get('parse_function'):
                if calls := v.get('calls'):
                    for call in calls:
                        url = f"/compute/v1/projects/{project_id}/{call}"
                        tasks.append(make_gcp_call(url, access_token, api_name='compute'))
        _ = await gather(*tasks)

        # Parse the data
        data = []
        for results in _:
            items = parse_results(results, parse_function)
            data.extend(items)

        # Add a new sheet with its data
        new_sheet = {k: {'description': v.get('description'), 'data': data}}
        sheets.update(new_sheet)

    # Create and save the Excel workbook
    _ = await write_to_excel(sheets)

if __name__ == "__main__":

    _ = run(main())
