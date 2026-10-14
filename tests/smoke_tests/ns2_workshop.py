"""Live NS2 native map origin evidence, using the engine's web API."""

import argparse
import json
import subprocess
import sys
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


def managed_container_name(env, server_name):
    """Resolve a managed Docker name, or None for a process server."""
    code = ('import sys; from server import Server; import server.runtime as runtime; '
            'metadata=runtime.resolve_runtime_metadata(Server(sys.argv[1])); '
            'print(metadata["container_name"] if metadata["runtime"]=="docker" else "")')
    result = subprocess.run([sys.executable, '-c', code, server_name], env=env,
                            check=True, capture_output=True, text=True, timeout=15)
    name = result.stdout.strip()
    if not name:
        return None
    if any(character.isspace() for character in name):
        raise ValueError('AlphaGSM did not resolve a single managed container name')
    return name


def _request_container_engine(container_name, port, user, password, actions):
    """Use the image's Python for authenticated native loopback HTTP, without publishing admin."""
    code = '''import json, sys
from urllib.parse import urlencode
from urllib.request import (Request, HTTPPasswordMgrWithDefaultRealm,
    HTTPDigestAuthHandler, HTTPBasicAuthHandler, ProxyHandler, build_opener)
port, user, password, actions = json.load(sys.stdin)
base = f'http://127.0.0.1:{int(port)}/'
credentials = HTTPPasswordMgrWithDefaultRealm()
credentials.add_password(None, base, user, password)
opener = build_opener(ProxyHandler({}), HTTPDigestAuthHandler(credentials), HTTPBasicAuthHandler(credentials))
request = Request(f'{base}?{urlencode(actions)}', headers={'Cache-Control': 'no-cache'})
with opener.open(request, timeout=10) as response:
    raw = response.read(1024 * 1024 + 1)
if len(raw) > 1024 * 1024:
    raise ValueError('NS2 native map API exceeded size limit')
print(json.dumps(json.loads(raw)))
'''
    result = subprocess.run(['docker', 'exec', '-i', container_name, 'python3', '-c', code],
                            input=json.dumps([port, user, password, actions]),
                            check=True, capture_output=True, text=True, timeout=20)
    return json.loads(result.stdout)


def read_map_origins(host, port, user, password, *, container_name=None):
    actions = {'request': 'getmaplist'}
    if container_name is not None:
        return _request_container_engine(container_name, port, user, password, actions)
    return _request_engine(host, port, user, password, actions)


def change_map(host, port, user, password, map_name, *, container_name=None):
    if not map_name or not all(char.isalnum() or char in '_-' for char in map_name):
        raise ValueError('Unsafe NS2 map name')
    actions = {'command': '1', 'rcon': f'sv_changemap {map_name}'}
    if container_name is not None:
        return _request_container_engine(container_name, port, user, password, actions)
    return _request_engine(host, port, user, password, actions)


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
