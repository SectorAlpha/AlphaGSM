"""Names reserved by ordinary top-level server dispatch and interactive setup."""

from server import Server

RESERVED_SERVER_NAMES = frozenset(
    (
        "help",
        "create",
        "up",
        "down",
        "shell",
        "logs",
        "compose",
        "ps",
        "self-update",
        "agent",
    )
    + Server.default_commands
)
