#!/usr/bin/env python3 

from asyncio import run, gather, create_task
from aiohttp import ClientSession
from google.auth import default
from google.auth.transport.requests import Request
import csv

CSV_FILE = 'gcp_projects.csv'


async def make_gcp_call(call: str, access_token: str, api_name: str) -> list:

    results = []

    call = call[1:] if call.startswith("/") else call
    url = f"https://{api_name}.googleapis.com/{call}"
    key = 'items' if api_name in ['compute', 'sqladmin'] else url.split("/")[-1]

    try:
        headers = {'Authorization': f"Bearer {access_token}"}
        params = {}
        async with ClientSession(raise_for_status=True) as session:
            while True:
                async with session.get(url, headers=headers, params=params) as response:
                    if int(response.status) == 200:
                        json = await response.json()
                        if 'aggregated/' in url:
                            items = json.get(key, {})
                            for k, v in items.items():
                                results.extend(v.get(url.split("/")[-1], []))
                        else:
                            results.extend(json.get(key, []))
                        if page_token := json.get('nextPageToken'):
                            params.update({'pageToken': page_token})
                        else:
                            break
                    else:
                        raise response
        return results
    except Exception as e:
        await session.close()
        return []


async def get_projects(access_token: str) -> list:

    projects = []

    try:
        api_name = "cloudresourcemanager"
        call = "/v1/projects"
        _ = await make_gcp_call(call, access_token, api_name)
        for project in _:
            projects.append({
                'name': project['name'],
                'number': str(project['projectNumber']),
                'id': project['projectId'],
                'created': project['createTime'],
                'state': project['lifecycleState'],
            })
        return projects
    except Exception as e:
        raise e


async def main():

    try:
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        credentials, project_id = default(scopes=scopes, quota_project_id=None)
        credentials.refresh(Request())
        access_token = credentials.token
        return await get_projects(access_token)
    except Exception as e:
        quit(e)


if __name__ == "__main__":

    _ = run(main())
    data = sorted(_, key=lambda x: x['number'], reverse=False)

    csvfile = open(CSV_FILE, 'w', newline='')
    writer = csv.writer(csvfile)
    writer.writerow(data[0].keys())
    [writer.writerow(row.values()) for row in data]
    csvfile.close()
