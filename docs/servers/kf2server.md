# Killing Floor 2

This guide covers the `kf2server` module in AlphaGSM.

`kf2server` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mykf2serve create kf2server
```

Run setup:

```bash
alphagsm mykf2serve setup
```

Start it:

```bash
alphagsm mykf2serve start
```

Check it:

```bash
alphagsm mykf2serve status
```

Stop it:

```bash
alphagsm mykf2serve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mykf2serve update
alphagsm mykf2serve backup
```

## Notes

- Module name: `kf2server`
- Default port: 7777
- Default Steam query port: 27015
- `query` and `info` use the configured A2S query port. Docker publishes this
  UDP listener separately from the gameplay port.
- The native Steam UDP listener uses the game port plus `12783`; AlphaGSM
  claims and publishes this port too.

## Workshop content

The native Workshop adapter accepts a public item or collection ID or Steam
Community URL, checks that it belongs to Killing Floor 2 (AppID `232090`),
and manages native server subscriptions and client downloads:

```bash
alphagsm mykf2serve stop
alphagsm mykf2serve mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=1208883070
alphagsm mykf2serve mod apply
alphagsm mykf2serve start
```

Start on the stock map first so the engine can download Workshop maps. Once a
map exists in the native cache, stop the server and select it with
`set startmap MAP_NAME`. The adapter uses `KFGame/Config/LinuxServer-KFEngine.ini`
on Linux and `PCServer-KFEngine.ini` on Windows. It preserves operator
subscriptions and unrelated settings, and refuses config changes while the
server runs. `mod cleanup` removes AlphaGSM's subscriptions and download-manager
entry; engine-generated cache files remain available on disk.

The public `KF-Corridor` fixture (`1208883070`) passed anonymous SteamCMD access
and the Linux engine's own Workshop download on 2026-10-13. The stock-map
AlphaGSM process run answered real A2S with `KF-BIOTICSLAB` and six slots.
Custom-map world loading and the complete Workshop smoke/integration lifecycle
are still pending; Workshop Docker validation is also pending.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create kf2server`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `configsubdir` | — | string | Relative config directory. |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `gametype` | — | string | Game mode class to start. |
| `port` | gameport | integer | Primary gameplay port. |
| `queryport` | — | integer | Steam query port. |
| `startmap` | map, gamemap, level, world | string | Starting map name. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/KFGameSteamServer.bin.x86_64`
- **Location**: `<install_dir>/Binaries/Win64/KFGameSteamServer.bin.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `232130`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/kf2server/](../server-templates/kf2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: Native subscription adapter; complete native load validation pending.
