import json
import yaml
import tomli
import tomli_w
import toml
import os
import pathlib
import platform
import openpyxl
import pprint


def get_home_dir() -> str:

    my_os = platform.system().lower()
    if my_os.startswith("win"):
        home_dir = os.environ.get("USERPROFILE")
        seperator = "\\Documents\\"
    elif my_os:
        home_dir = os.environ.get("HOME")
        seperator = "/"
        if my_os.startswith("darwin"):
            separator = "/Documents/"

    return home_dir + seperator


async def write_to_excel(sheets: dict, file_name: str = "gcp_network_data.xlsx", start_row: int = 1):

    #wb_data = {field: list(sheets[field]) for field in list(sheets.keys())}
    output_file = f"{get_home_dir()}{file_name}"

    wb = openpyxl.Workbook()
    for k, v in sheets.items():

        # Create worksheet
        sheet_name = v.get('sescription', k)
        ws = wb.create_sheet(sheet_name)
        data = v.get('data', [])

        # Skip if the data doesn't have at least one row or first row isn't a dictionary
        if len(data) < 1 or not isinstance(data[0], dict):
            continue

        # Write field names in the first row
        num_columns = 0
        column_widths = {}
        for column_index, column_name in enumerate(data[0].keys()):
            ws.cell(row=start_row, column=column_index + 1).value = column_name
            num_columns += 1
            column_widths[column_index] = len(str(column_name))

        # Write out rows of data
        for row_num in range(len(data)):
            row = list(data[row_num].values())
            ws.append(row)

            # Keep track of the largest value for each column
            for column_index, entry in enumerate(row):
                column_width = len(str(entry)) if entry else 0
                if column_index in column_widths:
                    if column_width > column_widths[column_index]:
                        column_widths[column_index] = column_width

        for i in range(num_columns):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = column_widths[i] + 1

    # Save the file
    wb.save(filename=output_file)
    print(f"Wrote data to file: {output_file}")


async def read_data_file(file_name: str, file_format: str = "toml") -> dict:

    if path := pathlib.Path(file_name):
        if path.is_file():
            with open(file_name, mode="rb") as fp:
                fn = file_name.lower()
                ff = file_name.upper()
                if fn.endswith('yaml') or fn.endswith('yml') or ff.startswith('yam'):
                    return yaml.load(fp, Loader=yaml.FullLoader)
                else:
                    return tomli.load(fp)


async def write_data_file(file_name: str, file_contents: list = [], file_format: str = "toml") -> dict:

    sub_dir = file_name.split('/')[0]
    if not os.path.exists(sub_dir):
        os.makedirs(sub_dir)

    with open(file_name, 'w') as f:
        match file_format:
            case 'json':
                _ = json.dumps(file_contents)
            case 'yaml':
                _ = yaml.dump(file_contents)
            case 'toml':
                _ = tomli_w.dumps({'items': file_contents})
            case other:
                _ = json.dumps(file_contents)
        f.write(_)


def write_to_bucket(bucket_name: str, file_name: str, data: str = ""):

    pass
