from server.settable_keys import resolve_requested_key

from gamemodules import inssserver
from gamemodules import scpslserver
from gamemodules import sevendaystodie
from gamemodules import soulmask
from gamemodules import stnserver
from gamemodules import thefrontserver
from gamemodules import twserver
from gamemodules import wreckfestserver


def test_hostname_style_servers_accept_servername_aliases():
    resolved = resolve_requested_key("servername", inssserver.setting_schema)

    assert resolved.canonical_key == "hostname"


def test_worldname_style_servers_accept_map_aliases():
    resolved = resolve_requested_key("map", thefrontserver.setting_schema)

    assert resolved.canonical_key == "worldname"


def test_adminpassword_style_servers_accept_adminpass_aliases():
    resolved = resolve_requested_key("adminpass", soulmask.setting_schema)

    assert resolved.canonical_key == "adminpassword"


def test_rconpassword_style_servers_accept_querypassword_aliases():
    resolved = resolve_requested_key("querypassword", scpslserver.setting_schema)

    assert resolved.canonical_key == "rconpassword"


def test_maxplayers_style_servers_accept_users_aliases():
    resolved = resolve_requested_key("users", thefrontserver.setting_schema)

    assert resolved.canonical_key == "maxplayers"


def test_servername_style_servers_accept_hostname_aliases():
    resolved = resolve_requested_key("hostname", twserver.setting_schema)

    assert resolved.canonical_key == "servername"


def test_port_style_servers_accept_gameport_aliases():
    resolved = resolve_requested_key("gameport", stnserver.setting_schema)

    assert resolved.canonical_key == "port"


def test_wreckfest_port_style_servers_accept_gameport_aliases():
    resolved = resolve_requested_key("gameport", wreckfestserver.setting_schema)

    assert resolved.canonical_key == "port"


def test_sevendaystodie_servername_style_servers_accept_hostname_aliases():
    resolved = resolve_requested_key("hostname", sevendaystodie.setting_schema)

    assert resolved.canonical_key == "servername"