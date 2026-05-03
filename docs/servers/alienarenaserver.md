# Alien Arena

This guide covers the `alienarenaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myalienare create alienarenaserver
```

Run setup:

```bash
alphagsm myalienare setup
```

Start it:

```bash
alphagsm myalienare start
```

Check it:

```bash
alphagsm myalienare status
```

Stop it:

```bash
alphagsm myalienare stop
```

## Setup Details

Setup configures:

- the game port (default 27910)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myalienare update
alphagsm myalienare backup
```

## Notes

- Module name: `alienarenaserver`
- Default port: 27910

## Developer Notes

### Run File

- **Executable**: `crx-dedicated`
- **Location**: `<install_dir>/crx-dedicated`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `629540`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/alienarenaserver/](../server-templates/alienarenaserver/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<game>/`
- **Mod directory**: `<install_dir>/<game>/`
- **Workshop support**: No

## Mod Sources

Alien Arena supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<game>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `game` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm myalienare mod add url https://example.com/mappack.pk3
alphagsm myalienare mod add url https://example.com/custom-content.zip
alphagsm myalienare mod apply
alphagsm myalienare mod cleanup
```
