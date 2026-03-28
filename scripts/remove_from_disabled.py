#!/usr/bin/env python3
"""Remove Windows-only server entries from disabled_servers.conf.

These servers have been converted to use Wine/Proton support,
so they no longer need to be disabled.

Usage: python3 scripts/remove_from_disabled.py
"""

from pathlib import Path

MODULES_TO_ENABLE = [
    "darkandlightserver",
    "fearthenightserver",
    "groundbranchserver",
    "motortownserver",
    "mythofempiresserver",
    "notdserver",
    "rs2server",
    "scumserver",
    "subsistenceserver",
    "remnantsserver",
    "askaserver",
    "astroneerserver",
    "battlecryoffreedomserver",
    "blackops3server",
    "blackwakeserver",
    "ducksideserver",
    "empyrionserver",
    "heatserver",
    "hellletlooseserver",
    "icarusserver",
    "lifeisfeudalserver",
    "medievalengineersserver",
    "miscreatedserver",
    "mw3server",
    "noonesurvivedserver",
    "outpostzeroserver",
    "pixarkserver",
    "primalcarnageextinctionserver",
    "readyornotserver",
    "reignofdwarfserver",
    "reignofkingsserver",
    "returntomoriaserver",
    "ror2server",
    "arksurvivalascended",
    "saleblazersserver",
    "sniperelite4server",
    "sonsoftheforestserver",
    "starruptureserver",
    "staxelserver",
    "sunkenlandserver",
    "terratechworldsserver",
    "theforestserver",
]

path = Path("disabled_servers.conf")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

new_lines = []
removed = []
for line in lines:
    # Tab-separated: module_name\treason
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        new_lines.append(line)
        continue
    module_name = stripped.split("\t")[0]
    if module_name in MODULES_TO_ENABLE:
        removed.append(module_name)
        continue
    new_lines.append(line)

path.write_text("".join(new_lines), encoding="utf-8")
print(f"Removed {len(removed)} entries from disabled_servers.conf:")
for m in removed:
    print(f"  {m}")
