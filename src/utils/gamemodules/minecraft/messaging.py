"""Shared messaging helpers for Minecraft-family server modules."""

import json
import re


def make_tellraw_message_hook(*, runtime_module):
    """Return a ``message`` hook that sends Minecraft ``tellraw`` commands."""

    def message(server, msg, *targets, parse=False):
        resolved_targets = list(targets) if targets else ["@a"]
        if parse and "@" in msg:
            msglist = []
            pattern = re.compile(r"([^@]*[^\\])?(@.(?:\[[^\]]+\])?)")
            while True:
                match = pattern.match(msg)
                if match is None:
                    break
                if match.group(1) is not None:
                    msglist.append(match.group(1))
                msglist.append({"selector": match.group(2)})
                msg = msg[match.end(0) :]
            msglist.append(msg)
            msgjson = json.dumps(msglist)
        else:
            msgjson = json.dumps({"text": msg})
        command = "\n".join(
            "tellraw " + target + " " + msgjson for target in resolved_targets
        )
        print(command)
        runtime_module.send_to_server(server, "\n" + command + "\n")

    message.__name__ = "message"
    return message