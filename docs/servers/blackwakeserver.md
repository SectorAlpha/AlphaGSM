# Blackwake

This guide covers the `blackwakeserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- Upstream `SERVER GUIDE.txt` in the install root explicitly documents
  **Windows-only** dedicated servers; Linux/Wine remains experimental in
  AlphaGSM and is not promoted to full lifecycle enablement yet.

## Quick Start

Create the server:

```bash
alphagsm myblackwak create blackwakeserver
```

Run setup:

```bash
alphagsm myblackwak setup
```

Start it:

```bash
alphagsm myblackwak start
```

Check it:

```bash
alphagsm myblackwak status
```

Stop it:

```bash
alphagsm myblackwak stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the Steam query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myblackwak update
alphagsm myblackwak backup
```

## Notes

- Module name: `blackwakeserver`
- Default game port: 7777
- Default query port: 27015
- Current validation status: still not enabled on Linux/Wine as of 2026-05-29, but materially closer. The bundled upstream `SERVER GUIDE.txt` still says Blackwake dedicated servers are Windows-only. AlphaGSM now avoids the regressed forced-Proton launch path on Linux, syncs `Server.cfg`, pins the documented `gamemode=7` dedicated startup path, disables bots by default with a managed password, and targets the declared Steam query port. A bounded 2026-05-29 host-Wine rerun then re-proved the managed AlphaGSM lifecycle can keep the `screen` session alive long enough for `query` and `info --json` to succeed on the managed `queryport`, and `stop` removed the live `screen` session again. The remaining gap is a fresh full checked-in setup-to-stop integration pass before promotion to enabled support.

## Developer Notes

### Run File

- **Executable**: `BlackwakeServer.exe`
- **Location**: `<install_dir>/BlackwakeServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `423410`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `54`
- **Upstream flow**: the bundled `SERVER GUIDE.txt` says the first `BlackwakeServer.exe -batchmode -nographics` launch generates `Server.cfg` and exits, and that alternate configs can be selected with `-configFile <name>`.
- **Managed defaults**: AlphaGSM now syncs `serverName`, `port`, `sport`, `gamemode=7`, and a default `serverpassword` into `Server.cfg` before launch. On the current headless Linux/Wine path it also forces `useBots=0`, and the active Linux launch path now prefers host `wine` over the regressed forced-Proton wrapper because bounded 2026-05-29 validation showed the Wine path could reach live A2S/info on the managed `queryport`.
- **Template**: See [server-templates/blackwakeserver/](../server-templates/blackwakeserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
