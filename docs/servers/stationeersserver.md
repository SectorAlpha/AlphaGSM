# Stationeers

This guide covers the `stationeersserver` module in AlphaGSM.

`stationeersserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection, and the validated SteamCMD-backed Linux
lifecycle stays aligned across both backends while local runs remain
process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- A Linux host/runtime that can start the Unity dedicated server cleanly in headless mode

## Native Workshop XML mods

Public Workshop XML gameplay mods use anonymous SteamCMD access. Add an item ID
or its Steam page URL; collections accept the same two forms:

```bash
alphagsm mystatione mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=3779655608
alphagsm mystatione mod apply
alphagsm mystatione mod list
```

AlphaGSM checks the consumer game ID (`544550`), `About/About.xml` identity,
and native `GameData` XML. It enables managed local packages in `modconfig.xml`
and preserves operator packages and settings. Code mods that need a separate
plugin loader are refused. Files edited outside AlphaGSM are preserved and
reported as a conflict.

The public [Mars Abandoned Frontier world](https://steamcommunity.com/sharedfiles/filedetails/?id=3779655608)
was downloaded anonymously and loaded through the process lifecycle on
13 October 2026. Its native log confirmed package loading and construction of
the `AbandonedMars` world; the engine-created save contains that world setting
and its structures. Workshop Docker validation is pending the test host's
SSD-backed Docker endpoint.

For a **new save**, select its world before starting:

```bash
alphagsm mystatione set savename frontier
alphagsm mystatione set worldname AbandonedMars
alphagsm mystatione start
```

Changing `worldname` does not convert an existing save. Keep the mods required
by saved worlds installed. After stopping, remove one desired item with
`mod remove workshop 3779655608`, then `mod apply`; `mod cleanup` removes all
AlphaGSM-owned activation and payload files and clears the desired list.
Downloaded Workshop cache files remain available for later use.

The smoke runner checks a fresh native log and reads the engine-created save
archive. Its process or Docker run is selected with
`ALPHAGSM_TEST_RUNTIME_BACKEND`; disposable integration installs can be reused
only through the explicit `ALPHAGSM_STATIONEERSSERVER_TEST_INSTALL` opt-in under
`ALPHAGSM_WORK_DIR`, with exclusive ownership by that test run.

## Quick Start

Create the server:

```bash
alphagsm mystatione create stationeersserver
```

Run setup:

```bash
alphagsm mystatione setup
```

Start it:

```bash
alphagsm mystatione start
```

Check it:

```bash
alphagsm mystatione status
```

Stop it:

```bash
alphagsm mystatione stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystatione update
alphagsm mystatione backup
```

## Notes

- Module name: `stationeersserver`
- Default game port: `27016/udp`
- Default update port: `27015/udp`
- AlphaGSM query/info contract: generic `udp` on the managed game port

<!-- alphagsm-server-variables:start -->

## Server variables

After `create stationeersserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `serverpassword` | sv_password, password | string | Password required to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `rocketstation_DedicatedServer.x86_64`
- **Location**: `<install_dir>/rocketstation_DedicatedServer.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `600760`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `10`
- **Template**: See [server-templates/stationeersserver/](../server-templates/stationeersserver/) if available
- **Current status**: A fresh smoke rerun and focused SteamCMD integration on 2026-05-29 now prove the post-September-2025 Linux launch shape end to end. AlphaGSM launches `rocketstation_DedicatedServer.x86_64 -file start ... -logFile ./server.log -settings ... UseSteamP2P false LocalIpAddress 0.0.0.0`, the shared setup port-retry helper handles the colliding default `updateport`, and the full lifecycle passes with generic `udp` `query`, `info`, `info --json`, and clean shutdown on the managed game port.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
