"""Show an ownership token on TeamSpeak, then ask Sector Alpha to query it."""

from .config import ConfigError
from .transport import QueryBusy, Transport, TransportError
from . import prove


def prove_binding(cfg, tag, binding_id, binding, token, transport=None):
    """Place one token, wait for the site query, and restore the previous name."""
    if binding["metadata"]["game_id"] != "ts3server":
        raise ConfigError("Name proof is available for TeamSpeak 3")
    value = cfg.load()
    if not value["reporting_enabled"] or not value["reporting"]:
        raise ConfigError("Reporting is disabled; use enable-reporting first")
    from server.server import Server
    from utils.query import ts3_serverinfo, ts3_set_name

    server = Server(tag)
    credentials = server.module.get_query_credentials(server)
    if not credentials:
        raise ConfigError("TeamSpeak ServerQuery login is not available on this server")
    query_port = int(server.data.get("queryport") or binding["metadata"]["port"])
    address = ("127.0.0.1", query_port)

    def read_name():
        return ts3_serverinfo(address[0], address[1], login=credentials)["name"]

    def write_name(name):
        ts3_set_name(address[0], address[1], name, login=credentials)

    client = (transport or Transport)(value["origin"])

    def request():
        try:
            return client.request(
                "POST",
                "/v1/agent/verify",
                credential=value["reporting"],
                payload={"binding_id": binding_id},
                timeout=20,
            )
        except QueryBusy as exc:
            raise prove.QueryBusy(str(exc)) from None

    def poll(job_id):
        return client.request(
            "GET",
            "/v1/agent/verify/" + job_id,
            credential=value["reporting"],
            timeout=20,
        )

    return prove.prove_name(
        tag,
        token,
        pending_path=cfg.root / "prove-name.json",
        read_name=read_name,
        write_name=write_name,
        request=request,
        poll=poll,
    )


def fetch_challenge(transport, value, binding_id):
    """Ask the associated agent API for one ownership token. A miss returns None."""
    if not value.get("reporting"):
        return None
    try:
        response = transport(value["origin"]).request(
            "POST",
            "/v1/agent/challenge",
            credential=value["reporting"],
            payload={"binding_id": binding_id},
            timeout=20,
        )
    except (TransportError, OSError, ValueError, RuntimeError):
        return None
    token = response.get("challenge") if isinstance(response, dict) else None
    if isinstance(token, str) and prove.TOKEN.fullmatch(token):
        return token
    return None
