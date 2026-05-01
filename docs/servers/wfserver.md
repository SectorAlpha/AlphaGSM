# Warfork

This guide covers the `wfserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywfserver create wfserver
```

Run setup:

```bash
alphagsm mywfserver setup
```

Start it:

```bash
alphagsm mywfserver start
```

Check it:

```bash
alphagsm mywfserver status
```

Stop it:

```bash
alphagsm mywfserver stop
```

## Setup Details

Setup configures:

- the game port (default 44400)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mywfserver update
alphagsm mywfserver backup
```

## Notes

- Module name: `wfserver`
- Default port: 44400

## Developer Notes

### Run File

- **Executable**: `wf_server.x86_64`
- **Location**: `<install_dir>/wf_server.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1136510`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/wfserver/](../server-templates/wfserver/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<fs_game>/`
- **Mod directory**: `<install_dir>/<fs_game>/`
- **Workshop support**: No

## Mod Sources

Warfork supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<fs_game>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `fs_game` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm mywfserver mod add url https://example.com/mappack.pk3
alphagsm mywfserver mod add url https://example.com/custom-content.zip
alphagsm mywfserver mod apply
alphagsm mywfserver mod cleanup
```
