#!/usr/bin/env python3

from platform import machine, release, system
from sys import version
from file_operations import read_data_file

SETTINGS_FILE = 'settings.yaml'
CALLS_FILE = 'calls.toml'


async def get_settings(settings_file: str = None) -> dict:

    try:
        settings_file = settings_file if settings_file else SETTINGS_FILE
        if settings := await read_data_file(settings_file):
            return settings
        else:
            raise f"Could not read settings file: '{settings_file}'"
    except Exception as e:
        raise e


async def get_calls(calls_file: str = None) -> dict:

    try:
        calls_file = calls_file if calls_file else CALLS_FILE
        if calls := await read_data_file(calls_file):
            return calls
        else:
            raise f"Could not read settings file: '{calls_file}'"
    except Exception as e:
        raise e


async def get_version(request: dict) -> dict:

    try:
        _ = {
            'os': "{} {}".format(system(), release()),
            'cpu': machine(),
            'python_version': str(version).split()[0],
            'server_protocol': "HTTP/" + request.get('http_version', "0/0"),
        }
        return _
    except Exception as e:
        raise e


