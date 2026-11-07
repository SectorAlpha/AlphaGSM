# Arma 3 headless client

This guide covers the `arma3headlessserver` module in AlphaGSM.

## Status

`arma3headlessserver` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Arma 3 dedicated server app `233780`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3hea create arma3headlessserver
```

Run setup:

```bash
alphagsm myarma3hea setup
```

Start it:

```bash
alphagsm myarma3hea start
```

Check it:

```bash
alphagsm myarma3hea status
```

Stop it:

```bash
alphagsm myarma3hea stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3hea update
alphagsm myarma3hea backup
```

## Notes

- Module name: `arma3headlessserver`
- Default port: 2302

<!-- alphagsm-server-variables:start -->

## Server variables

After `create arma3headlessserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `password` | — | string | Password required to connect to the Arma 3 server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `arma3server_x64`
- **Location**: `<install_dir>/arma3server_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `233780`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/arma3headlessserver/](../server-templates/arma3headlessserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
