# ASKA

This guide covers the `askaserver` module in AlphaGSM.

`askaserver` is `ENABLED (AUTH)`. The dedicated server installs anonymously,
but Steam requires a game-server login token generated for ASKA app `1898300`
before the server can start and appear in matchmaking.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- A [Steam game-server login token](https://steamcommunity.com/dev/managegameservers)
  generated for app `1898300`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myaskaserv create askaserver
```

Run setup:

```bash
alphagsm myaskaserv setup
```

Store the token, then start the server:

```bash
alphagsm myaskaserv set authenticationtoken YOUR_GSLT
alphagsm myaskaserv start
```

Check it:

```bash
alphagsm myaskaserv status
```

Stop it:

```bash
alphagsm myaskaserv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the Steam query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myaskaserv update
alphagsm myaskaserv backup
```

## Notes

- AlphaGSM writes the server identity, password, ports, region, and token to
  the upstream `server properties.txt` file and launches with
  `-propertiesPath "server properties.txt"`.
- Linux process launches require `xvfb-run` to provide the display used during
  Wine initialization. The shared Wine/Proton Docker image supplies it when
  using the Docker runtime.
- Module name: `askaserver`
- Default game port: 7777
- Default query port: 27015

## Developer Notes

### Run File

- **Executable**: `AskaServer.exe`
- **Location**: `<install_dir>/AskaServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3246670`

### Server Configuration

- **Config file**: `server properties.txt`
- **Max players**: `4`
- **Template**: See [server-templates/askaserver/](../server-templates/askaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
