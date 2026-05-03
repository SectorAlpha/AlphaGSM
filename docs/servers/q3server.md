# Quake 3 Arena

This guide covers the `q3server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq3server create q3server
```

Run setup:

```bash
alphagsm myq3server setup
```

Start it:

```bash
alphagsm myq3server start
```

Check it:

```bash
alphagsm myq3server status
```

Stop it:

```bash
alphagsm myq3server stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myq3server update
alphagsm myq3server backup
```

## Mod Sources

Quake 3 content management currently targets the active `fs_game` directory
under the server root. By default that is `baseq3/`, but if you set a custom
`fs_game` value, AlphaGSM installs into that directory instead.

- Current mod source support is direct `url` entries only.
- `mod add url <https-url>` accepts direct `.pk3` URLs and supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload exposes either `<fs_game>/<name>.pk3` or bare `.pk3` files at the archive root.
- `mod cleanup` removes only AlphaGSM-tracked `.pk3` files and keeps its cache/state under `.alphagsm/mods/q3server/`.
- The first Q3 slice intentionally stops at `.pk3` content and does not try to install arbitrary extracted scripts or binaries.

Examples:

```bash
alphagsm myq3server mod add url https://example.invalid/mappack.zip
alphagsm myq3server mod add url https://example.invalid/pak-custom.pk3
alphagsm myq3server mod apply
alphagsm myq3server mod cleanup
```

## Notes

- Module name: `q3server`
- Default port: 27960

## Developer Notes

### Run File

- **Executable**: `q3ded.x86_64`
- **Location**: `<install_dir>/q3ded.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `baseq3/server.cfg`)
- `set servername`, `set fs_game`, and `set map` rewrite `<fs_game>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/q3server/](../server-templates/q3server/) if available

### Maps and Mods

- **Map directory**: `<fs_game>/` (default `baseq3/`)
- **Mod directory**: `<fs_game>/` (default `baseq3/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for Quake 3, install approved `.pk3` payloads into the active `fs_game` directory, and clean up only AlphaGSM-managed files from `.alphagsm/mods/q3server/`.
- **Workshop support**: No
