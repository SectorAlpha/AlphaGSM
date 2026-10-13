"""Stage a disposable authenticated DST cluster and verify native mod execution."""

import argparse
import configparser
from pathlib import Path
import re
import shutil
import time

WORKSHOP_ITEM_ID = "378160973"
WORKSHOP_ITEM_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id=378160973"


def stage_cluster(source, destination, game_port, query_port, auth_port):
    """Copy only the selected cluster's credentials/configuration, never its world."""
    source, destination = Path(source), Path(destination)
    required = ("cluster.ini", "cluster_token.txt", "Master/server.ini")
    optional = ("Master/worldgenoverride.lua", "Master/leveldataoverride.lua",
                "Master/worldsettings_overrides.lua")
    if destination.exists():
        raise ValueError("Disposable DST cluster destination already exists")
    if (source / "Master").is_symlink() or any(
        (source / relative).is_symlink() or not (source / relative).is_file()
        for relative in required
    ):
        raise ValueError("DST fixture requires regular cluster.ini, cluster_token.txt and Master/server.ini")
    if not (source / "cluster_token.txt").read_bytes().strip():
        raise ValueError("DST fixture requires a nonempty Klei cluster token")
    configs = {}
    try:
        for relative in ("cluster.ini", "Master/server.ini"):
            config = configparser.ConfigParser(interpolation=None)
            config.read_string((source / relative).read_text(encoding="utf-8-sig"))
            configs[relative] = config
    except (configparser.Error, UnicodeError) as exc:
        raise ValueError("DST fixture has invalid INI configuration") from exc
    for relative in optional:
        if (source / relative).is_symlink():
            raise ValueError("DST fixture configuration must not be symlinked")
    destination.joinpath("Master").mkdir(parents=True)
    for relative in (*required, *optional):
        original = source / relative
        if original.is_file():
            target = destination / relative
            shutil.copyfile(original, target)
            target.chmod(0o600)
    changes = {
        "cluster.ini": {"NETWORK": {"cluster_name": "AlphaGSM Workshop Validation"},
                        "SHARD": {"shard_enabled": "false"}},
        "Master/server.ini": {"NETWORK": {"server_port": str(game_port)},
                              "STEAM": {"master_server_port": str(query_port),
                                        "authentication_port": str(auth_port)},
                              "SHARD": {"is_master": "true"}},
    }
    for relative, sections in changes.items():
        config = configs[relative]
        for section, values in sections.items():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in values.items():
                config.set(section, key, value)
        with (destination / relative).open("w", encoding="utf-8") as handle:
            config.write(handle)


def assert_workshop_loaded(log_text, item_id=WORKSHOP_ITEM_ID):
    """Require native modmain execution followed by a successful Lua bootstrap."""
    pattern = r"Mod:\s+workshop-" + re.escape(str(item_id)) + r"\b[^\r\n]*\bLoading modmain\.lua\b"
    loads = list(re.finditer(pattern, log_text))
    assert loads, "DST engine has not executed the requested Workshop modmain.lua"
    completed = log_text.find("LOADING LUA SUCCESS", loads[-1].end())
    assert completed >= 0, "DST Workshop modmain execution has no successful Lua bootstrap"
    execution = log_text[loads[-1].start():completed]
    assert not re.search(r"LUA ERROR|Error loading mod|error calling|MOD ERROR", execution, re.I), (
        "DST reported a Lua/mod error after the requested Workshop execution"
    )


def wait_for_workshop_loaded(log_path, timeout_seconds):
    """Wait on the fresh shard log; missing/failed execution is a failure."""
    log_path = Path(log_path)
    deadline = time.monotonic() + timeout_seconds
    reason = "DST shard server_log.txt was not created"
    while time.monotonic() < deadline:
        if log_path.is_file():
            try:
                assert_workshop_loaded(log_path.read_text(errors="replace"))
                return
            except AssertionError as exc:
                reason = str(exc)
        time.sleep(2)
    raise AssertionError(reason)


def main():
    """Expose the same fixture and load checks to the streamed smoke runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    stage = commands.add_parser("stage")
    stage.add_argument("source", type=Path)
    stage.add_argument("destination", type=Path)
    stage.add_argument("game_port", type=int)
    stage.add_argument("query_port", type=int)
    stage.add_argument("auth_port", type=int)
    verify = commands.add_parser("verify")
    verify.add_argument("log_path", type=Path)
    verify.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if args.action == "stage":
        stage_cluster(args.source, args.destination, args.game_port, args.query_port, args.auth_port)
    else:
        wait_for_workshop_loaded(args.log_path, args.timeout)
        print("DST engine executed Global Positions and completed its Lua bootstrap")


if __name__ == "__main__":
    main()
