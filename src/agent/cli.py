"""Local interactive enrollment and explicit opt-in; no secret CLI arguments."""

import argparse
import getpass
import json
from .config import Config, ConfigError, local_tag
from .contracts import ACTIONS
from .service import Service
from .transport import Transport, TransportError
from . import onboarding
from .publication_config import PublicationConfigError, local_publication
from .dns_lookup import PreflightError
from . import endpoint_check
from . import prove
from . import local_query
from . import name_proof
from .binding_ports import selected_ports


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
        command_parser = commands.add_parser(command)
        if command == "enroll":
            command_parser.add_argument("--origin")
    replacement = commands.add_parser("replace-credential")
    replacement.add_argument("scope", choices=("reporting", "management"))
    for command in ("bind", "setup"):
        bind = commands.add_parser(command)
        if command == "bind":
            bind.add_argument("target", help="One local tag, '*' for all, or a legacy binding ID")
            bind.add_argument("local_tag", nargs="?", help="Legacy exact local tag")
        else:
            bind.set_defaults(target="*", local_tag=None)
        bind.add_argument("--binding-id")
        bind.add_argument("--origin")
        bind.add_argument("--epoch", type=int, default=1)
        bind.add_argument("--actions", nargs="*", choices=sorted(ACTIONS))
        publication = bind.add_mutually_exclusive_group()
        publication.add_argument("--publish", action="store_true", default=None)
        publication.add_argument("--private", action="store_false", dest="publish")
        bind.add_argument("--game")
        bind.add_argument("--host")
        bind.add_argument("--public-ip", action="append", help="Expected public machine IP; repeat for multiple IPs")
        bind.add_argument("--port", type=int, help="Advertised query port; Minecraft also uses it for players")
        bind.add_argument("--connect-port", type=int, help="Advertised player connection port (for example NAT)")
        bind.add_argument("--name")
        bind.add_argument("--capacity", type=int)
    check = commands.add_parser("check-endpoint")
    check.add_argument("local_tag")
    check.add_argument("--public-ip", action="append")
    unbind = commands.add_parser("unbind")
    unbind.add_argument("binding_id")
    publication = commands.add_parser("publication")
    publication.add_argument("binding_id")
    publication.add_argument("selection", choices=("on", "off"))
    proof = commands.add_parser("prove")
    proof.add_argument("local_tag")
    queried = commands.add_parser("query")
    queried.add_argument("local_tag")
    try:
        options = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code
    try:
        cfg = Config(root)
        if options.command == "enroll":
            onboarding.enroll(cfg, options.origin, Transport)
        elif options.command == "replace-credential":
            key_id = input("Rotated key ID: ").strip()
            secret = getpass.getpass("Rotated credential secret: ").strip()
            generation = int(input("New management generation: ")) if options.scope == "management" else None
            cfg.replace_credential(options.scope, key_id, secret, generation=generation)
            print("Selected credential replaced. Existing local permissions are unchanged.")
        elif options.command in ("bind", "setup"):
            if options.local_tag is None:
                return onboarding.guided(cfg, options, Transport)
            if options.binding_id is not None or any(
                getattr(options, key) is None for key in ("game", "host", "port", "name")
            ):
                raise ConfigError("Legacy bind requires exact game, host, port and name")
            if options.publish is True and options.game == "ts3server":
                from .choices import TEAMSPEAK_DIRECTORY

                raise ConfigError(TEAMSPEAK_DIRECTORY)
            if options.publish is True and options.game not in onboarding.PROFILES:
                raise ConfigError("This game has no supported public query profile")
            # Verify that the local target exists under this user's normal AlphaGSM namespace.
            from .lifecycle import AlphaRuntime

            with AlphaRuntime().lock(local_tag(options.local_tag)):
                local = onboarding.read_local(options.local_tag)
                if local['game_id'] != options.game:
                    raise ConfigError("Selected game does not match the local server module")
            ports = selected_ports(local, {}, options)
            cfg.bind(
                options.target,
                options.local_tag,
                options.epoch,
                actions=options.actions or [],
                publication=options.publish is True,
                metadata={
                    "game_id": options.game,
                    "host": options.host,
                    **ports,
                    "name": options.name,
                    "capacity": options.capacity or 0,
                },
                **local_publication(options.public_ip),
            )
            print("Exact local binding saved. Only the selected operations are permitted.")
            print("Advertised host=" + options.host + " | player port=" + str(ports['connect_port'] or 'unknown') +
                  " | query port=" + str(ports['port']))
            if "stop" in (options.actions or []) or "restart" in (options.actions or []):
                print("Normal AlphaGSM stop may force termination after graceful shutdown attempts.")
        elif options.command == "check-endpoint":
            tag = local_tag(options.local_tag)
            matches = [binding for binding in cfg.load()['bindings'].values() if binding['tag'] == tag]
            if len(matches) != 1:
                raise ConfigError("Bind this exact local server tag before checking its public endpoint")
            endpoint_check.check_endpoint(matches[0], options.public_ip)
            print("Public endpoint check passed for " + tag + ". The central ownership challenge is still required.")
        elif options.command == "unbind":
            cfg.unbind(options.binding_id)
        elif options.command == "publication":
            cfg.publication(options.binding_id, options.selection == "on")
        elif options.command == "prove":
            return _prove(cfg, options.local_tag)
        elif options.command == "query":
            from utils.query import QueryError

            try:
                local_query.query_tag(cfg, options.local_tag)
            except QueryError as exc:
                print("Query failed: " + str(exc))
                return 1
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
    except (ConfigError, PreflightError, PublicationConfigError) as exc:
        print("Agent operation rejected: " + str(exc))
        return 1
    except (ValueError, OSError, RuntimeError, EOFError):
        print("Agent operation rejected; check local policy, permissions and provider availability.")
        return 1
    except KeyboardInterrupt:
        return 130


def _prove(cfg, tag):
    """Place the account's ownership token on TeamSpeak and wait for the site query."""
    tag = local_tag(tag)
    matches = [(key, item) for key, item in cfg.load()["bindings"].items() if item["tag"] == tag]
    if len(matches) != 1:
        raise ConfigError("Bind this exact local server tag before proving its name")
    binding_id, binding = matches[0]
    value = cfg.load()
    token = name_proof.fetch_challenge(Transport, value, binding_id)
    if token is None:
        token = getpass.getpass("Ownership challenge: ").strip()
    from utils.query import QueryError

    try:
        result = name_proof.prove_binding(cfg, tag, binding_id, binding, token)
    except prove.QueryBusy:
        print("Sector Alpha is still querying this server. The previous TeamSpeak name has been restored. Try again.")
        return 1
    except ValueError as exc:
        print(str(exc))
        return 1
    except QueryError as exc:
        print("TeamSpeak name proof failed: " + str(exc).split(":", 1)[0])
        return 1
    except TransportError:
        print("Sector Alpha did not accept the check. Create a fresh website challenge and try again.")
        return 1
    if result.get("verified") is True:
        print("Control verified. The previous TeamSpeak name has been restored.")
    else:
        print("The name check did not verify. The previous TeamSpeak name has been restored.")
    return 0


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
