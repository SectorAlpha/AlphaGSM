# Empyrion - Galactic Survival

This guide covers the `empyrionserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myempyrion create empyrionserver
```

Run setup:

```bash
alphagsm myempyrion setup
```

Start it:

```bash
alphagsm myempyrion start
```

Check it:

```bash
alphagsm myempyrion status
```

Stop it:

```bash
alphagsm myempyrion stop
```

## Setup Details

Setup configures:

- the game port (default 30000)
- the historical `queryport` value (default 30004)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myempyrion update
alphagsm myempyrion backup
```

## Notes

- Module name: `empyrionserver`
- Default game port: 30000
- Default stored `queryport`: 30004
- Upstream `dedicated.yaml` documents `30004` as `Tel_Port`, not as a confirmed A2S query endpoint

## Developer Notes

### Run File

- **Executable**: `DedicatedServer/EmpyrionDedicated.exe`
- **Location**: `<install_dir>/DedicatedServer/EmpyrionDedicated.exe`
- **Linux launch shape**: `DedicatedServer/EmpyrionDedicated.exe -batchmode -nographics -dedicated dedicated.yaml`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `530870`

Current Linux host validation no longer uses `EmpyrionLauncher.exe`, because the
launcher exits after spawning the real dedicated child and tears down the
temporary `xvfb-run` display with it. AlphaGSM now keeps the direct dedicated
process alive under Proton plus `xvfb-run`, but focused Linux host validation on
2026-05-28 still stopped before any proven game/query readiness:

- AlphaGSM stored explicit host ports like `46319` and `42657` in the server
  data during focused integration runs, but the installed `dedicated.yaml`
  remained at the upstream default `Srv_Port: 30000`, so the current module
  still does not sync its configured runtime port into Empyrion's real server
  config.
- The server-owned dedicated log under `server/Logs/5046/Dedicated_*.log`
  stopped at Unity bootstrap with `Failed to create batch mode window:
  Success.` and never reached a later startup banner, bound-port message, or
  query-ready marker.
- A manual reproduction of
  `DedicatedServer/EmpyrionDedicated.exe -batchmode -nographics -dedicated dedicated.yaml`
  under Proton plus `xvfb-run` on 2026-05-28 also produced no fresh
  server-owned runtime log or bound-port evidence within 45 seconds.

The next bounded runtime/query fix is therefore to wire real Empyrion config
sync first, then re-prove which live port/protocol AlphaGSM should use for
`query` and `info`. Until that happens, `30004` remains only the documented
`Tel_Port`, not a confirmed A2S endpoint.

### Server Configuration

- **Config files**: `dedicated.yaml`
- **Template**: See [server-templates/empyrionserver/](../server-templates/empyrionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
