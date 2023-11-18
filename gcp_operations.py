import platform
import json
import google.oauth2
import google.auth
import google.auth.transport.requests
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


async def make_gcp_call(call: str, access_token: str, api_name: str) -> list:

    results = []

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
                        json = await response.json()
                        if 'aggregated/' in url:
                            if key == 'items':
                                items = json.get(key, {})
                                for k, v in items.items():
                                     results.extend(v.get(url.split("/")[-1], []))
                        else:
                            #print(key)
                            results.append(json.get(key)) if key == 'result' else results.extend(json.get(key, []))
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
        _ = await make_gcp_call('/v1/projects', access_token, api_name='cloudresourcemanager')
        _ = sorted(_, key=lambda x: x.get('name'), reverse=False)
        for project in _:
            projects.append({
                'name': project['name'],
                'id': project['projectId'],
                'number': project['projectNumber'],
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
