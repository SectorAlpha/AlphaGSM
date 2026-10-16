"""Terminal relay for Source engines behind the Docker runtime console FIFO."""

import shlex


def build_source_container_start_command(server, command_getter):
    """Give Source a real input terminal without changing process launch commands."""
    command, working_dir = command_getter(server)
    return (["/usr/bin/script", "--quiet", "--flush", "--return", "--command",
             shlex.join(command), "/dev/null"], working_dir)
