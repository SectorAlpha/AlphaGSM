# Sniper Elite 4

This guide covers the `sniperelite4server` module in AlphaGSM.

`sniperelite4server` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- Docker for the validated Linux runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- For local non-Docker launches on Linux: Wine or Proton plus `xvfb-run`

## Quick Start

Create the server:

```bash
alphagsm mysniperel create sniperelite4server
```

Run setup:

```bash
alphagsm mysniperel setup
```

Start it:

```bash
alphagsm mysniperel start
```

Check it:

```bash
alphagsm mysniperel status
```

Stop it:

```bash
alphagsm mysniperel stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the authentication port (`game port + 1`)
- the update port (`game port + 2`)
- the lobby port (`game port + 3`)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mysniperel update
alphagsm mysniperel backup
```

## Notes

- Module name: `sniperelite4server`
- Default game port: 7777
- Port layout: game UDP, auth UDP, update UDP, lobby TCP
- `query`, `info`, and `info --json` use generic UDP health on the managed
  game port
- Current validation status: historically `PASSED` on the Docker-backed
  `wine-proton` runtime; the corrected four-port/config contract is pending
  the replacement GitHub CI run

<!-- alphagsm-server-variables:start -->

## Server variables

After `create sniperelite4server`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `maxplayers` | users | integer | The maximum number of players. |
| `port` | gameport | integer | The game port for the server. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `bin/SniperElite4_Dedicated.exe`
- **Location**: `<install_dir>/bin/SniperElite4_Dedicated.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `568880`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `12`
- **Linux support note**: the validated Linux path now runs through AlphaGSM's
  Docker-backed `wine-proton` runtime image rather than a host `screen`
  session. AlphaGSM stages `default.cfg` in the install root before launch,
  copying the shipped `Docs/ExampleConfigs/Example1.cfg` when available so the
  dedicated server no longer aborts immediately on `default.cfg` lookup. If no
  map rotation is present, AlphaGSM adds `VILLAGE DM` as the minimum startup
  map and preserves any operator-defined rotation entries.
- **Host process display**: AlphaGSM explicitly enables Wine's X11 driver
  inside its 24-bit Xvfb display, including under inherited headless CI
  settings.
- **Managed directives**: `Server.Name`, `Server.GamePort`,
  `Server.AuthPort`, `Server.UpdatePort`, `Server.LobbyPort`,
  `Settings.MaxPlayers`, and `Server.Host`
- **Template**: See [server-templates/sniperelite4server/](../server-templates/sniperelite4server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
