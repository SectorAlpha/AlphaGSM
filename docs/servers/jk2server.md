# Jedi Knight II: Jedi Outcast

This guide covers the `jk2server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myjk2serve create jk2server
```

Run setup:

```bash
alphagsm myjk2serve setup
```

Start it:

```bash
alphagsm myjk2serve start
```

Check it:

```bash
alphagsm myjk2serve status
```

Stop it:

```bash
alphagsm myjk2serve stop
```

## Setup Details

Setup configures:

- the game port (default 28070)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myjk2serve update
alphagsm myjk2serve backup
```

## Notes

- Module name: `jk2server`
- Default port: 28070

## Developer Notes

### Run File

- **Executable**: `jk2mvded.x86_64`
- **Location**: `<install_dir>/jk2mvded.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/jk2server/](../server-templates/jk2server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<fs_game>/`
- **Mod directory**: `<install_dir>/<fs_game>/`
- **Workshop support**: No

## Mod Sources

Jedi Outcast supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<fs_game>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `fs_game` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm myjk2serve mod add url https://example.com/mappack.pk3
alphagsm myjk2serve mod add url https://example.com/custom-content.zip
alphagsm myjk2serve mod apply
alphagsm myjk2serve mod cleanup
```
