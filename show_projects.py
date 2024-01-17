#!/usr/bin/env python3

from asyncio import run, gather
#from file_operations import write_to_excel
from gcp_operations import get_projects, make_api_call
from auth_operations import get_adc_token


async def main():

    try:
        access_token = await get_adc_token()
    except Exception as e:
        quit(e)

    # Get projects and create first sheet
    projects = await get_projects(access_token, sort_by='created')
    if len(projects) < 1:
        quit("Didn't find any projects")

    urls = [f"https://cloudresourcemanager.googleapis.com/v1/projects/{project['id']}" for project in projects]
    tasks = (make_api_call(url, access_token) for url in urls)
    await gather(*tasks)
        #print(_)

    return projects

if __name__ == "__main__":

    _ = run(main())
    print(len(_))
