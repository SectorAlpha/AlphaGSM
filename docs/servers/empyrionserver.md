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
- A bounded AlphaGSM-managed host repro on 2026-05-29 kept the direct dedicated
  process alive for 240 seconds, synced `ServerConfig.Srv_Port` to `46319`,
  created `Saves/Games/DediGame`, and advanced the stable dedicated log
  (`Logs/alphagsm-dedicated.log`) through `Loading file '.../dedicated.yaml'`
  to `Started a new game`. Even at that later state, repeated `ss -lpun` checks
  still showed no listener on either the synced main port (`46319`) or the
  documented telnet port (`30004`), and AlphaGSM `query` / `info --json`
  continued to fail with `TCP ping failed: [Errno 111] Connection refused`.
- A bounded launcher repro of `EmpyrionLauncher.exe -startDedi` under the same
  wrapper still exits immediately, spawns a detached child that AlphaGSM cannot
  supervise directly, and the child only logged the old `Failed to create batch
  mode window: Success.` line before stalling.

The next bounded runtime/query fix is to re-prove which live port/protocol
AlphaGSM should use for `query` and `info` now that `Srv_Port` sync is in
place, the direct dedicated log is stable, and the dedicated process can reach
`Started a new game` without ever exposing a reachable listener. Until that
happens, `30004` remains only the documented `Tel_Port`, not a confirmed A2S
endpoint, and the synced game port still has no proven listener contract under
the current host Wine/Proton path.

### Server Configuration

- **Config files**: `dedicated.yaml`
- **Template**: See [server-templates/empyrionserver/](../server-templates/empyrionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
