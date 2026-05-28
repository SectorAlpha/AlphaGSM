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
- Default stored `queryport`: 30004
- Upstream `dedicated.yaml` documents `30004` as `Tel_Port`, not as a confirmed A2S query endpoint

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
wrapper screen log. Focused Linux host validation on 2026-05-29 still stopped
before any proven game/query readiness:

- `queryport` remains a stored AlphaGSM value with default `30004`, but
  upstream `dedicated.yaml` documents that number as `Tel_Port`, not as a
  confirmed A2S query endpoint. The module does not currently claim a proven
  native query-port mapping beyond syncing the main game port.
- A bounded direct repro of
  `DedicatedServer/EmpyrionDedicated.exe -batchmode -nographics -logFile Logs/alphagsm-dedicated.log -dedicated dedicated.yaml`
  under Proton plus `xvfb-run` on 2026-05-29 progressed past the earlier Unity
  bootstrap blind spot and into the dedicated log with `Loading file
  '.../dedicated.yaml'` and `Started a new game`, but still produced no proven
  UDP/TCP listener or AlphaGSM query/info readiness within the bounded probe
  window.
- A bounded launcher repro of `EmpyrionLauncher.exe -startDedi` under the same
  wrapper still exits immediately, spawns a detached child that AlphaGSM cannot
  supervise directly, and the child only logged the old `Failed to create batch
  mode window: Success.` line before stalling.

The next bounded runtime/query fix is to re-prove which live port/protocol
AlphaGSM should use for `query` and `info` now that `Srv_Port` sync is in
place and the direct dedicated log is stable. Until that happens, `30004`
remains only the documented `Tel_Port`, not a confirmed A2S endpoint.

### Server Configuration

- **Config files**: `dedicated.yaml`
- **Template**: See [server-templates/empyrionserver/](../server-templates/empyrionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
