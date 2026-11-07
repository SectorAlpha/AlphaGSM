"""Reactive Drop native engine map ownership evidence over authenticated RCON."""

import re

from utils.query import _source_rcon_command_once


def native_map_owners(text):
    """Read actual engine Workshop mappings; never infer ownership from filenames."""
    return {name: item for name, item in re.findall(
        r'^\s*maps/([A-Za-z0-9_-]+)\.bsp\s+->\s+([1-9][0-9]*)\s*$', text, re.MULTILINE)}


def query_native_maps(host, port, password):
    return native_map_owners(_source_rcon_command_once(
        host, port, password, 10, 'rd_dump_workshop_mapping_server maps/'))


def change_map(host, port, password, map_name):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', map_name):
        raise ValueError('Unsafe Reactive Drop map name')
    return _source_rcon_command_once(host, port, password, 10, f'changelevel {map_name}')
