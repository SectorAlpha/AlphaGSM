#!/usr/bin/env python3
"""Update TEST_STATUS.md to reflect the 42 modules moved from DISABLED to SKIPPED."""

import re

STATUS_FILE = "docs/TEST_STATUS.md"

# 42 modules moved from DISABLED to SKIPPED, with their exe basenames and app IDs
MOVED_MODULES = {
    "arksurvivalascended": ("ArkAscendedServer.exe", "2430930"),
    "askaserver": ("AskaServer.exe", "3246670"),
    "astroneerserver": ("AstroServer.exe", "728470"),
    "battlecryoffreedomserver": ("BCoF.exe", "1362540"),
    "blackops3server": ("BlackOps3Server.exe", "545990"),
    "blackwakeserver": ("Blackwake Dedicated Server.exe", "423410"),
    "darkandlightserver": ("DNLServer.exe", "630230"),
    "ducksideserver": ("DucksideServer.exe", "2690320"),
    "empyrionserver": ("EmpyrionDedicated.exe", "530870"),
    "fearthenightserver": ("MoonlightServer.exe", "764940"),
    "groundbranchserver": ("GroundBranchServer-Win64-Shipping.exe", "476400"),
    "heatserver": ("HeatServer.exe", "996600"),
    "hellletlooseserver": ("HLLServer.exe", "822500"),
    "icarusserver": ("IcarusServer.exe", "2089300"),
    "lifeisfeudalserver": ("ddctd_cm_yo_server.exe", "320850"),
    "medievalengineersserver": ("MedievalEngineersDedicated.exe", "367970"),
    "miscreatedserver": ("MiscreatedServer.exe", "302200"),
    "motortownserver": ("MotorTownServer-Win64-Shipping.exe", "2223650"),
    "mw3server": ("iw5mp_server.exe", "115310"),
    "mythofempiresserver": ("MOEServer.exe", "1794810"),
    "noonesurvivedserver": ("WRSHServer.exe", "2329680"),
    "notdserver": ("LFServer.exe", "1420710"),
    "outpostzeroserver": ("OutpostZeroServer.exe", "762880"),
    "pixarkserver": ("PixARKServer.exe", "824360"),
    "primalcarnageextinctionserver": ("PCEdedicated.exe", "336400"),
    "readyornotserver": ("ReadyOrNotServer.exe", "950290"),
    "reignofdwarfserver": ("ReignOfDwarfServer.exe", "1999160"),
    "reignofkingsserver": ("Server.exe", "381690"),
    "remnantsserver": ("StartServer.bat", "1141420"),
    "returntomoriaserver": ("MoriaServer.exe", "3349480"),
    "ror2server": ("Risk of Rain 2.exe", "1180760"),
    "rs2server": ("VNGame.exe", "418480"),
    "saleblazersserver": ("Saleblazers.exe", "3099600"),
    "scumserver": ("SCUMServer.exe", "3792580"),
    "sniperelite4server": ("SniperElite4_DedicatedServer.exe", "568880"),
    "sonsoftheforestserver": ("SonsOfTheForestDS.exe", "2465200"),
    "starruptureserver": ("StarRuptureServerEOS.exe", "3809400"),
    "staxelserver": ("Staxel.ServerWizard.exe", "755170"),
    "subsistenceserver": ("run_dedicated_server.bat", "1362640"),
    "sunkenlandserver": ("Sunkenland-DedicatedServer.exe", "2667530"),
    "terratechworldsserver": ("TT2Server.exe", "2533070"),
    "theforestserver": ("TheForestDedicatedServer.exe", "556450"),
}

with open(STATUS_FILE) as f:
    content = f.read()

# 1. Update summary table counts
content = re.sub(r"(\| DISABLED \|)\s*124\s*\|", r"\1 82    |", content)
content = re.sub(r"(\| SKIPPED  \|)\s*50\s*\|",  r"\1 92    |", content)

# 2. Update DISABLED section header (currently says 126, should now be 82)
content = re.sub(r"## DISABLED \(\d+\)", "## DISABLED (82)", content)

# 3. Remove the 42 rows from the DISABLED table
for mod in MOVED_MODULES:
    # Match lines like "| modname | ... |" (possibly with different whitespace)
    content = re.sub(
        r"\| " + re.escape(mod) + r" \|[^\n]*\n",
        "",
        content,
    )

# 4. Update SKIPPED section header
content = re.sub(r"## SKIPPED \(\d+\)", "## SKIPPED (92)", content)

# 5. Build the 42 new SKIPPED rows and insert them after the existing enshrouded/stormworksserver rows
new_rows = []
for mod in sorted(MOVED_MODULES):
    exe, app = MOVED_MODULES[mod]
    new_rows.append(
        f"| {mod} | Requires Wine or Proton-GE; Windows binary ({exe}) via SteamCMD app {app}; run scripts/install_proton.sh |"
    )

# Insert after the stormworksserver line (which is currently the last proton entry)
insert_after = "| stormworksserver | Requires Wine or Proton-GE; Windows binary (server64.exe) via SteamCMD app 1247090; run scripts/install_proton.sh |"
insert_block = insert_after + "\n" + "\n".join(new_rows)
content = content.replace(insert_after, insert_block)

with open(STATUS_FILE, "w") as f:
    f.write(content)

print(f"Updated {STATUS_FILE}")
print(f"  DISABLED: 124 → 82")
print(f"  SKIPPED:  50  → 92")
print(f"  Added {len(new_rows)} rows to SKIPPED table")
print(f"  Removed {len(MOVED_MODULES)} rows from DISABLED table")
