"""Local interactive enrollment and explicit opt-in; no secret CLI arguments."""

import argparse
import getpass
import json
from .config import Config, ConfigError, local_tag
from .contracts import ACTIONS
from .service import Service
from .transport import Transport, TransportError


def run(args, *, root=None):
    parser = argparse.ArgumentParser(prog="alphagsm agent")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in (
        "enroll",
        "status",
        "enable-reporting",
        "disable-reporting",
        "enable-management",
        "disable-management",
        "run",
        "report-once",
        "forget",
    ):
        commands.add_parser(command)
    replacement = commands.add_parser("replace-credential")
    replacement.add_argument("scope", choices=("reporting", "management"))
    bind = commands.add_parser("bind")
    bind.add_argument("binding_id")
    bind.add_argument("local_tag")
    bind.add_argument("--epoch", type=int, default=1)
    bind.add_argument("--actions", nargs="*", choices=sorted(ACTIONS), default=[])
    bind.add_argument("--publish", action="store_true")
    bind.add_argument("--game", required=True, choices=("teamfortress2", "minecraft.vanilla", "minecraft.paper"))
    bind.add_argument("--host", required=True)
    bind.add_argument("--port", required=True, type=int)
    bind.add_argument("--name", required=True)
    bind.add_argument("--capacity", type=int, default=0)
    unbind = commands.add_parser("unbind")
    unbind.add_argument("binding_id")
    publication = commands.add_parser("publication")
    publication.add_argument("binding_id")
    publication.add_argument("selection", choices=("on", "off"))
    try:
        options = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code
    try:
        cfg = Config(root)
        if options.command == "enroll":
            api_origin = input("Compatible HTTPS origin: ").strip()
            code = getpass.getpass("Single-use enrollment code: ").strip()
            response = Transport(api_origin).request("POST", "/v1/agent/enroll", payload={"code": code})
            cfg.enroll(api_origin, response)
            print("Enrolled. Reporting and management remain disabled until you enable each locally.")
        elif options.command == "replace-credential":
            key_id = input("Rotated key ID: ").strip()
            secret = getpass.getpass("Rotated credential secret: ").strip()
            generation = int(input("New management generation: ")) if options.scope == "management" else None
            cfg.replace_credential(options.scope, key_id, secret, generation=generation)
            print("Selected credential replaced. Existing local permissions are unchanged.")
        elif options.command == "bind":
            # Verify that the local target exists under this user's normal AlphaGSM namespace.
            from server.server import Server
            from .lifecycle import AlphaRuntime

            with AlphaRuntime().lock(local_tag(options.local_tag)):
                server = Server(options.local_tag)
                if server.data["module"] != options.game:
                    raise ConfigError("Selected game does not match the local server module")
            cfg.bind(
                options.binding_id,
                options.local_tag,
                options.epoch,
                actions=options.actions,
                publication=options.publish,
                metadata={
                    "game_id": options.game,
                    "host": options.host,
                    "port": options.port,
                    "name": options.name,
                    "capacity": options.capacity,
                },
            )
            print("Exact local binding saved. Only the selected operations are permitted.")
            if "stop" in options.actions or "restart" in options.actions:
                print("Normal AlphaGSM stop may force termination after graceful shutdown attempts.")
        elif options.command == "unbind":
            cfg.unbind(options.binding_id)
        elif options.command == "publication":
            cfg.publication(options.binding_id, options.selection == "on")
        elif options.command in ("enable-reporting", "disable-reporting", "enable-management", "disable-management"):
            scope = options.command.split("-")[1]
            cfg.enable(**{scope: options.command.startswith("enable")})
            if options.command == "disable-reporting":
                # Explicit best-effort withdrawal; an offline publication lease expires.
                if cfg.load()["reporting"]:
                    try:
                        Service(cfg).report_once()
                    except TransportError:
                        print("Offline: publication will expire within ten minutes of the last accepted renewal.")
            if options.command == "enable-management":
                print(
                    "Remote operations use normal local stop/restart semantics, including possible force termination."
                )
        elif options.command == "status":
            value = cfg.load()
            print(
                json.dumps(
                    {
                        k: value[k]
                        for k in ("installation_id", "reporting_enabled", "management_enabled", "policy_version")
                    },
                    sort_keys=True,
                )
            )
        elif options.command == "run":
            Service(cfg).run()
        elif options.command == "report-once":
            value = cfg.load()
            if not value["reporting_enabled"]:
                raise ConfigError("Reporting is disabled; use enable-reporting first")
            Service(cfg).report_once()
        elif options.command == "forget":
            cfg.forget()
        return 0
    except (ConfigError, ValueError, OSError, RuntimeError):
        print("Agent operation rejected; check local policy, permissions and provider availability.")
        return 1
    except KeyboardInterrupt:
        return 130


def notify_success(tag):
    """Durable reconciliation hint only; outages never affect local command success."""
    try:
        from .config import default_root

        if not (default_root() / "config.json").exists():
            return
        cfg = Config()
        value = cfg.load()
        if value["reporting_enabled"] and any(b["tag"] == tag for b in value["bindings"].values()):
            cfg.changed()
    except (ValueError, OSError):
        pass
