# Alien Arena

This guide covers the `alienarenaserver` module in AlphaGSM.

`alienarenaserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that staged-server-tree
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- a native Alien Arena dedicated server tree containing `crx-dedicated`
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

`alienarenaserver` is supported in `ENABLED (BYO)` mode. The current anonymous
SteamCMD app does not deliver the native server payload, so before `setup` or
`start` you should stage a native Alien Arena dedicated server tree containing
`crx-dedicated` inside your chosen `<install_dir>/`.

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

Suggested flow:

```bash
alphagsm myalienare create alienarenaserver
alphagsm myalienare setup -n 27910 /path/to/alienarena
# copy crx-dedicated and the rest of the native server tree into /path/to/alienarena/
alphagsm myalienare start
```

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
