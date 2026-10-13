"""Require fresh running-engine evidence for extracted Workshop addons."""

import argparse
import json
from pathlib import Path
import re
import zlib


def assert_workshop_mounts(log_text, item_ids, token):
    """Require engine VFS content and ULib execution from a completed Lua probe."""
    log_text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", log_text)
    lines = [line.strip() for line in log_text.splitlines()]
    starts = [index for index, line in enumerate(lines) if line == f"BEGIN-{token}"]
    assert starts, "No fresh Garry's Mod Workshop probe began"
    start = starts[-1]
    ends = [index for index in range(start + 1, len(lines)) if lines[index] == f"END-{token}"]
    assert ends, "Garry's Mod Workshop probe did not complete"
    mounted = set()
    for line in lines[start + 1:ends[0]]:
        try:
            addon = json.loads(line)
        except ValueError:
            continue
        if isinstance(addon, dict) and addon.get("mounted") is True:
            item_id = str(addon.get("workshop_id"))
            if item_id == "557962238" and addon.get("ulib_loaded") is not True:
                continue
            if item_id == "557962280" and addon.get("ulx_loaded") is not True:
                continue
            mounted.add(item_id)
    missing = set(map(str, item_ids)) - mounted
    assert not missing, f"Garry's Mod engine did not load Workshop addons: {sorted(missing)}"


def probe_command(token, probes):
    """Read addon content via engine VFS, comparing against its installed CRC."""
    commands = [f'print("BEGIN-{token}")']
    for probe in probes:
        item_id, path, crc = probe["workshop_id"], probe["path"], probe["crc"]
        commands.append(f'local data=file.Read({json.dumps(path)},"GAME") '
                        'print(util.TableToJSON({'
                        f'workshop_id="{item_id}",mounted=data~=nil and util.CRC(data)=="{crc}",'
                        'ulib_loaded=istable(ULib) and istable(ULib.ucl) and isfunction(ULib.ucl.query),'
                        'ulx_loaded=istable(ulx) and isfunction(ulx.command)}))')
    commands.append(f'print("END-{token}")')
    return " ".join(commands)


def build_probes(data):
    """Choose one addon-only virtual file per tracked Workshop item."""
    root = Path(data["dir"])
    probes = []
    for entry in data["mods"]["installed"]:
        if entry["source_type"] != "workshop":
            continue
        item_id = entry["resolved_id"].removeprefix("workshop.")
        prefix = f"garrysmod/addons/{item_id}/"
        paths = sorted(entry["installed_files"])
        assert paths and all(path.startswith(prefix) for path in paths), "Unexpected Workshop ownership"
        selected = next((path for path in paths if "/lua/autorun/" in path), paths[0])
        probes.append({"workshop_id": item_id, "path": selected[len(prefix):],
                       "crc": str(zlib.crc32((root / selected).read_bytes()))})
    assert probes, "No installed Workshop addon content to probe"
    return probes


def write_probe(data, token):
    """Use a test-owned Lua file to avoid Source console command-length limits."""
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,100}", token), "Unsafe probe token"
    name = f"alphagsm_workshop_{token}.lua"
    script = Path(data["dir"]) / "garrysmod" / "lua" / name
    script.write_text(probe_command(token, build_probes(data)), encoding="utf-8")
    return f"lua_openscript {name}"


def main():
    """Share engine verification between smoke and pytest lifecycle runners."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path", type=Path)
    parser.add_argument("token")
    parser.add_argument("item_ids", nargs="+")
    args = parser.parse_args()
    assert_workshop_mounts(args.log_path.read_text(errors="replace"), args.item_ids, args.token)
    print(f"Garry's Mod loaded all {len(args.item_ids)} Workshop addon payloads")


if __name__ == "__main__":
    main()
