"""Bounded ARK world readiness beyond the initial empty Steam response."""
import time

import pytest


def wait_for_loaded_world(read_info, timeout, *, clock=time.monotonic, sleep=time.sleep):
    """Require a named native world and positive player capacity within one deadline."""
    deadline = clock() + timeout
    last = None
    while clock() < deadline:
        last = read_info(deadline - clock())
        name, maximum = last.get("map"), last.get("max_players")
        if (isinstance(name, str) and name.strip() and name.lower() != "unknown"
                and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0):
            return last
        sleep(min(2, max(0, deadline - clock())))
    pytest.fail(f"ARK never reported a loaded world with positive capacity: {last!r}")
