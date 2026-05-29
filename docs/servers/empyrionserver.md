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
- the derived TCP status port (`queryport`, default `port + 3`)
- the install directory
- SteamCMD downloads the Windows dedicated server files
- when `dedicated.yaml` exists, AlphaGSM syncs the configured game port into
  `ServerConfig.Srv_Port` during install, update, `set port`, and pre-start

## Useful Commands

```bash
alphagsm myempyrion update
alphagsm myempyrion backup
```

## Notes

- Module name: `empyrionserver`
- Default game port: 30000
- Default stored `queryport`: `port + 3` (`30003` by default)
- AlphaGSM `query`, `info`, and `info --json` use the live STCP TCP listener on `port + 3`
- Upstream `dedicated.yaml` still documents `30004` as `Tel_Port`; AlphaGSM does not rely on that fixed legacy value for runtime readiness

## Developer Notes

### Run File

- **Executable**: `DedicatedServer/EmpyrionDedicated.exe`
- **Location**: `<install_dir>/DedicatedServer/EmpyrionDedicated.exe`
- **Linux launch shape**: `DedicatedServer/EmpyrionDedicated.exe -batchmode -nographics -logFile Logs/alphagsm-dedicated.log -dedicated dedicated.yaml`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `530870`

Current Linux host validation no longer uses `EmpyrionLauncher.exe`, because the
launcher exits after spawning the real dedicated child and tears down the
temporary `xvfb-run` display with it. AlphaGSM keeps the direct dedicated
binary as the intended host Wine/Proton contract, and the module now syncs
`ServerConfig.Srv_Port` in `dedicated.yaml` from the AlphaGSM-owned `port`
value and pins the Linux dedicated log to `Logs/alphagsm-dedicated.log` so
smoke/integration read the actual server-owned runtime log instead of only the
wrapper screen log. Focused Linux host validation on 2026-05-29 proved the live
runtime/query surface:

- the direct dedicated process reaches `Started a new game` under the managed
  Wine/Proton launch path
- AlphaGSM syncs `ServerConfig.Srv_Port` from the owned game port into
  `dedicated.yaml`
- the live AlphaGSM readiness/query/info surface is the generic TCP STCP
  listener on `port + 3`, which Empyrion logs as `STCP: Now listening for
  PfServers on port <port + 3>`
- `query`, `info`, and `info --json` now use that derived TCP listener instead
  of the older stale fixed-`30004` / A2S assumption

`EmpyrionLauncher.exe -startDedi` remains intentionally unused on Linux because
the launcher exits after spawning a detached child and tears down the temporary
display with it. The supervised direct dedicated binary remains the supported
AlphaGSM contract.

### Server Configuration

- **Config files**: `dedicated.yaml`
- **Template**: See [server-templates/empyrionserver/](../server-templates/empyrionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
