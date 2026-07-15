# Quake 4

This guide covers the `q4server` module in AlphaGSM.

`q4server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that archive-or-staged-tree prerequisite,
while local runs remain process-backed by default unless you opt into the
Docker backend.

## Requirements

- `screen`
- either a direct Quake 4 dedicated-server archive URL or a pre-staged Quake 4
  Linux dedicated server tree
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq4server create q4server
```

Run setup:

```bash
alphagsm myq4server setup
```

`q4server` is supported in `ENABLED (BYO)` mode. Before `setup` or `start`,
either:

- set `url` to a working Quake 4 dedicated-server archive, or
- stage `q4ded.x86` and the rest of the Quake 4 server files inside your
  chosen `<install_dir>/`

The historical default archive URL is no longer available. Use a verified
operator-supplied archive URL or stage the server tree and required game data.

Start it:

```bash
alphagsm myq4server start
```

Check it:

```bash
alphagsm myq4server status
```

Stop it:

```bash
alphagsm myq4server stop
```

## Setup Details

Setup configures:

- the game port (default 28004)
- the install directory
- downloads and extracts the server archive when `url` is set

Suggested flow:

```bash
alphagsm myq4server create q4server
alphagsm myq4server set url https://example.invalid/q4-dedicated.tar.gz
alphagsm myq4server setup -n 28004 /path/to/q4
alphagsm myq4server start
```

Or, if you already have the server files:

```bash
alphagsm myq4server create q4server
alphagsm myq4server setup -n 28004 /path/to/q4
# copy q4ded.x86 and the rest of the server tree into /path/to/q4/
alphagsm myq4server start
```

## Useful Commands

```bash
alphagsm myq4server update
alphagsm myq4server backup
alphagsm myq4server set servername "AlphaGSM Q4"
alphagsm myq4server set map q4dm6
alphagsm myq4server set url https://example.invalid/q4-dedicated.tar.gz
```

`set servername`, `set fs_game`, and `set map` rewrite `<fs_game>/server.cfg` immediately through the schema-backed config-sync path.

## Notes

- Module name: `q4server`
- Default port: 28004

## Developer Notes

### Run File

- **Executable**: `q4ded.x86`
- **Location**: `<install_dir>/q4ded.x86`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `q4base/server.cfg`)
- **Template**: See [server-templates/q4server/](../server-templates/q4server/) if available
- **Schema-backed sync**: AlphaGSM keeps `hostname`, `fs_game`, and `startmap` aligned with `set`

### Maps and Mods

- **Map directory**: `<install_dir>/<fs_game>/`
- **Mod directory**: `<install_dir>/<fs_game>/`
- **Workshop support**: No

## Mod Sources

Quake 4 supports AlphaGSM-managed direct `url` mod sources for content-only `.pk4` payloads.

Supported payload shapes:

- a direct `.pk4` URL
- an archive containing bare `.pk4` files at the archive root
- an archive containing `<fs_game>/<name>.pk4`

AlphaGSM installs approved `.pk4` content into the active `fs_game` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm myq4server mod add url https://example.com/mappack.pk4
alphagsm myq4server mod add url https://example.com/custom-content.zip
alphagsm myq4server mod apply
alphagsm myq4server mod cleanup
```
