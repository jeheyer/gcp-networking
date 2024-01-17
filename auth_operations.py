import google.auth
import google.auth.transport.requests
import google.oauth2
import platform
import json

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']


async def get_adc_token():

    try:
        credentials, project_id = google.auth.default(scopes=SCOPES, quota_project_id=None)
        _ = google.auth.transport.requests.Request()
        credentials.refresh(_)
        return credentials.token  # return access token
    except Exception as e:
        raise e


async def read_service_account_key(file: str) -> dict:

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

