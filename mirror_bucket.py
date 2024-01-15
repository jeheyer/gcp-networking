#!/usr/bin/env python3
import traceback
from asyncio import run, gather
from sys import argv
from math import ceil
from storage_operations import get_storage_token, list_storage_objects, get_storage_object
from file_operations import write_file

PARALLEL_DOWNLOADS = 20

"""
script that simply mirrors a GCS bucket to local files
"""


async def main(bucket_name: str, prefix: str, service_file: str):

    try:
        token = await get_storage_token(service_file)
        object_names = await list_storage_objects(bucket_name, token, prefix if prefix else "")
    except Exception as e:
        await token.close()
        raise e

    pages = ceil(len(object_names) / PARALLEL_DOWNLOADS)
    for page in range(0, pages):
        start = page * PARALLEL_DOWNLOADS
        end = start + PARALLEL_DOWNLOADS
        o = object_names[start:end]
        try:
            #print(len(o))
            tasks = [get_storage_object(bucket_name, token, object_name) for object_name in o]
            blobs = await gather(*tasks)
            blobs = dict(zip(o, blobs))
            for object_name, blob in blobs.items():
                await write_file(object_name, blob)
        except Exception as e:
            await token.close()
            raise e

    await token.close()

if __name__ == '__main__':

    try:
        arg_names = ['bucket_name', 'prefix', 'service_file']
        if len(argv) > len(arg_names):
            args = [argv[i+1] for i, v in enumerate(arg_names)]
            run(main(args[0], args[1], args[2]))
        else:
            message = f"Usage: {argv[0]}"
            for arg_name in arg_names:
                message += f" <{arg_name}>"
            quit(message)
    except Exception as e:
        quit(traceback.format_exc())
