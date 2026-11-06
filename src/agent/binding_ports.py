"""Select approved public player/query ports without changing live local settings."""

from .contracts import integer


def selected_ports(local, approved, options, *, query_port=None):
    """Infer only while binding; keep existing approvals unless explicitly overridden."""
    query = options.port if options.port is not None else approved.get('port', local['port'])
    connect = approved.get('connect_port', local['connect_port'])
    if options.connect_port is not None:
        connect = options.connect_port
    elif local['game_id'].startswith('minecraft.') and (
            options.port is not None or (query_port is not None and query_port != query
                and approved.get('connect_port') in (None, approved.get('port')))):
        connect = query if query_port is None else query_port
    if connect is not None:
        integer(connect, 1, 65535)
    return {'port': query if query_port is None else query_port, 'connect_port': connect}
