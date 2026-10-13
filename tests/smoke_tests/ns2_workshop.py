"""Live NS2 native map origin evidence, using the engine's web API."""

import argparse
import json
from urllib.parse import urlencode
from urllib.request import (Request, HTTPPasswordMgrWithDefaultRealm,
                            HTTPDigestAuthHandler, HTTPBasicAuthHandler, build_opener)


def assert_map_origin(payload, map_name, item_id):
    """Match an engine-resolved map to its exact published Workshop ID."""
    assert isinstance(payload, list), 'NS2 engine map list is not an array'
    for entry in payload:
        if not isinstance(entry, dict) or entry.get('name', '').lower() != map_name.lower():
            continue
        value = entry.get('modId')
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value == int(item_id):
            return
        if isinstance(value, str):
            try:
                radix = 10 if value.isdecimal() else 16
                if int(value.removeprefix('0x'), radix) == int(item_id):
                    return
            except ValueError:
                pass
    raise AssertionError(f'NS2 engine map {map_name} is not attributed to Workshop item {item_id}')


def _request_engine(host, port, user, password, actions):
    base = f'http://{host}:{int(port)}/'
    credentials = HTTPPasswordMgrWithDefaultRealm()
    credentials.add_password(None, base, user, password)
    opener = build_opener(HTTPDigestAuthHandler(credentials), HTTPBasicAuthHandler(credentials))
    request = Request(f'{base}?{urlencode(actions)}', headers={'Cache-Control': 'no-cache'})
    with opener.open(request, timeout=10) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('NS2 native map API exceeded size limit')
    return json.loads(raw)


def read_map_origins(host, port, user, password):
    return _request_engine(host, port, user, password, {'request': 'getmaplist'})


def change_map(host, port, user, password, map_name):
    if not map_name or not all(char.isalnum() or char in '_-' for char in map_name):
        raise ValueError('Unsafe NS2 map name')
    return _request_engine(host, port, user, password,
                           {'command': '1', 'rcon': f'sv_changemap {map_name}'})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host'); parser.add_argument('port',type=int)
    parser.add_argument('user'); parser.add_argument('password')
    parser.add_argument('map_name'); parser.add_argument('item_id')
    args=parser.parse_args()
    assert_map_origin(read_map_origins(args.host,args.port,args.user,args.password),args.map_name,args.item_id)
    print('Engine confirmed selected NS2 map belongs to its Workshop item')


if __name__=='__main__':
    main()
