"""Internal bounded subprocess adapter for the fixed local runtime operations."""

from contextlib import redirect_stdout, redirect_stderr, nullcontext
import os
from utils.state_io import inherited_state_lock
import json
from .config import local_tag


class Discard:
    def write(self, text):
        return len(text)

    def flush(self):
        pass


def main(args):
    if len(args) not in (2, 3) or args[1] not in ("status", "start", "stop", "restart"):
        return 2
    tag, action = local_tag(args[0]), args[1]
    with redirect_stdout(Discard()), redirect_stderr(Discard()):
        from server.server import Server, DATAPATH
        from server.runtime import get_runtime

        lock = inherited_state_lock(os.path.join(DATAPATH, tag + ".json"), int(args[2])) if len(args) == 3 else nullcontext()
        with lock:
            server = Server(tag)
            dispatch = {"start": Server.start, "stop": Server.stop, "restart": Server.restart}
            if action == "status":
                result = "running" if get_runtime(server).is_running(server) else "stopped"
            else:
                dispatch[action](server)
                result = None
    print(json.dumps(result))
    return 0
