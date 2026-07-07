# Call of Duty 2

This guide covers the `cod2server` module in AlphaGSM.

`cod2server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that owned-base-assets
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- owned base-game multiplayer assets that include `main/localized_*.iwd` and
  `main/default_localize_mp.cfg`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycod2serv create cod2server
```

Run setup:

```bash
alphagsm mycod2serv setup
```

Start it:

```bash
alphagsm mycod2serv start
```

Check it:

```bash
alphagsm mycod2serv status
```

Stop it:

```bash
alphagsm mycod2serv stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the official Linux dedicated-server archive
- still requires copied retail/localized multiplayer assets before the server
  can finish startup

`cod2server` is supported in `ENABLED (BYO)` mode. AlphaGSM installs the Linux
dedicated binary for you, but the official archive still does not include the
localized retail files the server expects at startup.

Before `start`, copy the required owned files from a legitimate Call of Duty 2
installation into the AlphaGSM server tree:

```text
<install_dir>/main/localized_*.iwd
<install_dir>/main/default_localize_mp.cfg
```

Minimal operator flow:

```bash
alphagsm mycod2serv create cod2server
alphagsm mycod2serv setup
cp /path/to/cod2/main/localized_*.iwd <install_dir>/main/
cp /path/to/cod2/main/default_localize_mp.cfg <install_dir>/main/
alphagsm mycod2serv start
```

If startup still reports missing localized assets, check that the files landed
under the server's `main/` directory, not a mod directory such as `uo/` or a
custom `moddir`.

## Useful Commands

```bash
alphagsm mycod2serv update
alphagsm mycod2serv backup
```

## Notes

- Module name: `cod2server`
- Default port: 28960
- Current blocker for anonymous installs: the official dedicated archive does
  not ship `main/localized_*.iwd` or `main/default_localize_mp.cfg`

## Developer Notes

### Run File

- **Executable**: `cod2_lnxded`
- **Location**: `<install_dir>/cod2_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Owned base assets still required**: `main/localized_*.iwd`,
  `main/default_localize_mp.cfg`
- **Copy target before first start**: `<install_dir>/main/`
- **Template**: See [server-templates/cod2server/](../server-templates/cod2server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/`
- **Workshop support**: No

## Mod Sources

Call of Duty 2 supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm mycod2serv mod add url https://example.com/mappack.pk3
alphagsm mycod2serv mod add url https://example.com/custom-content.zip
alphagsm mycod2serv mod apply
alphagsm mycod2serv mod cleanup
```
