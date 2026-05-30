# Return to Castle Wolfenstein

This guide covers the `rtcwserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`
- Original Return to Castle Wolfenstein multiplayer assets in `main/`
  - `mp_bin.pk3`
  - `mp_pak0.pk3` through `mp_pak5.pk3`
  - `mp_pakmaps0.pk3` through `mp_pakmaps6.pk3`

## Quick Start

Create the server:

```bash
alphagsm myrtcwserv create rtcwserver
```

Run setup:

```bash
alphagsm myrtcwserv setup
```

Start it:

```bash
alphagsm myrtcwserv start
```

Check it:

```bash
alphagsm myrtcwserv status
```

Stop it:

```bash
alphagsm myrtcwserv stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

This server is supported in `ENABLED (BYO)` mode. Before `start`, copy the original RTCW multiplayer pk3 set into the install's
`main/` directory. The public ioRTCW engine release is not enough by itself for
the dedicated multiplayer server.

## Useful Commands

```bash
alphagsm myrtcwserv update
alphagsm myrtcwserv backup
```

## Mod Sources

RTCW content management currently targets the active `fs_game` directory under
the server root. By default that is `main/`, but if you set a custom `fs_game`
value, AlphaGSM installs into that directory instead.

- Current mod source support is direct `url` entries only.
- `mod add url <https-url>` accepts direct `.pk3` URLs and supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload exposes either `<fs_game>/<name>.pk3` or bare `.pk3` files at the archive root.
- `mod cleanup` removes only AlphaGSM-tracked `.pk3` files and keeps its cache/state under `.alphagsm/mods/rtcwserver/`.
- The first RTCW slice intentionally stops at `.pk3` content and does not try to install arbitrary extracted scripts or binaries.

Examples:

```bash
alphagsm myrtcwserv mod add url https://example.invalid/mappack.zip
alphagsm myrtcwserv mod add url https://example.invalid/pak-custom.pk3
alphagsm myrtcwserv mod apply
alphagsm myrtcwserv mod cleanup
```

## Notes

- Module name: `rtcwserver`
- Default port: 27960

## Developer Notes

### Run File

- **Executable**: `iowolfded.x86_64`
- **Location**: `<install_dir>/iowolfded.x86_64`
- **Engine**: Custom
- **Owned assets required before start**: `main/mp_bin.pk3`, `main/mp_pak0.pk3` through `main/mp_pak5.pk3`, and `main/mp_pakmaps0.pk3` through `main/mp_pakmaps6.pk3`

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set fs_game`, and `set map` rewrite `<fs_game>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/rtcwserver/](../server-templates/rtcwserver/) if available

### Maps and Mods

- **Map directory**: `<fs_game>/` (default `main/`)
- **Mod directory**: `<fs_game>/` (default `main/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for RTCW, install approved `.pk3` payloads into the active `fs_game` directory, and clean up only AlphaGSM-managed files from `.alphagsm/mods/rtcwserver/`.
- **Workshop support**: No
