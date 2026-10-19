"""Local anonymous status query. The result is not sent to Sector Alpha."""

from server.public_query import protocol_for, query_public
from utils.query import QueryError, ts3_serverinfo

from .config import ConfigError, local_tag


def observe_local(server, game_id, *, timeout=5.0):
    """Read one local server with the same anonymous protocol the website uses."""
    protocol = protocol_for(game_id)
    if protocol is None:
        raise QueryError("This game has no anonymous status query")
    host, port = _endpoint(server, protocol)
    if protocol == "ts3":
        info = ts3_serverinfo(host, port, timeout=timeout)
        players, capacity = info["clients_online"], info["max_clients"]
        if type(players) is not int or type(capacity) is not int or players < 0 or capacity < 0:
            raise QueryError("TeamSpeak returned invalid player counts")
        if capacity < players:
            capacity = players
        return {"name": info["name"], "players": players, "capacity": capacity, "version": info["version"]}
    return query_public(game_id, host, port, timeout=timeout)


def query_tag(cfg, tag, *, timeout=5.0, open_server=None):
    """Print a local status query for one bound tag. Nothing is uploaded."""
    tag = local_tag(tag)
    matches = [(key, item) for key, item in cfg.load()["bindings"].items() if item["tag"] == tag]
    if len(matches) != 1:
        raise ConfigError("Bind this exact local server tag before querying it")
    _binding_id, binding = matches[0]
    game_id = binding["metadata"]["game_id"]
    if open_server is None:
        from server.server import Server

        open_server = Server
    observation = observe_local(open_server(tag), game_id, timeout=timeout)
    print("Local query for " + tag + " (" + game_id + "). This result is not sent to Sector Alpha.")
    print("name=" + observation.get("name", ""))
    print("players=" + str(observation["players"]) + "/" + str(observation["capacity"]))
    if observation.get("map"):
        print("map=" + observation["map"])
    if observation.get("version"):
        print("version=" + observation["version"])
    return observation


def _endpoint(server, protocol):
    module = server.module
    for name in ("get_info_address", "get_query_address"):
        hook = getattr(module, name, None)
        if not callable(hook):
            continue
        host, port, hooked = hook(server)
        if hooked == protocol:
            return str(host), int(port)
    if protocol == "a2s":
        import server.runtime as runtime_module

        port = server.data.get("queryport", server.data["port"])
        return str(runtime_module.resolve_query_host(server)), int(port)
    raise QueryError("This game has no anonymous status query")
