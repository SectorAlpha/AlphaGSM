# Life is Feudal: Your Own

This guide covers the `lifeisfeudalserver` module in AlphaGSM.

## Support Status

`lifeisfeudalserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can stage
the server files, but `start` still requires an operator-provided local
MySQL/MariaDB service reachable on `localhost`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- a local MySQL or MariaDB service reachable on `localhost:3306`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylifeisfe create lifeisfeudalserver
```

Run setup:

```bash
alphagsm mylifeisfe setup
```

Start it:

```bash
alphagsm mylifeisfe start
```

Check it:

```bash
alphagsm mylifeisfe status
```

Stop it:

```bash
alphagsm mylifeisfe stop
```

## Setup Details

Setup configures:

- the game port (default 28001)
- the install directory
- SteamCMD downloads the server files

## Bring Your Own Steps

1. Run `alphagsm mylifeisfe create lifeisfeudalserver`.
2. Run `alphagsm mylifeisfe setup`.
3. Start or provision a local MySQL/MariaDB service on `localhost` before
   running `alphagsm mylifeisfe start`.
4. Keep that database service running while AlphaGSM manages the server.

If `start` reports an `ENABLED (BYO)` MySQL requirement, verify that a local
database listener is reachable on `localhost:3306` and retry.

## Useful Commands

```bash
alphagsm mylifeisfe update
alphagsm mylifeisfe backup
```

## Notes

- Module name: `lifeisfeudalserver`
- Default port: 28001

## Developer Notes

### Run File

- **Executable**: `ddctd_cm_yo_server.exe`
- **Location**: `<install_dir>/ddctd_cm_yo_server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `320850`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/lifeisfeudalserver/](../server-templates/lifeisfeudalserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
