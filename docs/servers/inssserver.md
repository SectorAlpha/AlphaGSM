# Insurgency: Sandstorm

This guide covers the `inssserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myinssserv create inssserver
```

Run setup:

```bash
alphagsm myinssserv setup
```

Start it:

```bash
alphagsm myinssserv start
```

Check it:

```bash
alphagsm myinssserv status
```

Stop it:

```bash
alphagsm myinssserv stop
```

## Setup Details

Setup configures:

- the game port (default 27131)
- the query port (default `port + 1`)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myinssserv update
alphagsm myinssserv backup
```

## Notes

- Module name: `inssserver`
- Default game port: 27131
- Default query port: `port + 1`

## Developer Notes

### Run File

- **Executable**: `InsurgencyServer-Linux-Shipping`
- **Location**: `<install_dir>/InsurgencyServer-Linux-Shipping`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `581330`

Smoke and integration validation wait for the startup log and then require
`alphagsm info --json` to report `a2s` on the Sandstorm query path.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `28`
- **Template**: See [server-templates/inssserver/](../server-templates/inssserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
