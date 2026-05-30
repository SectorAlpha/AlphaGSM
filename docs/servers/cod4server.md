# Call of Duty 4

This guide covers the `cod4server` module in AlphaGSM.

## Requirements

- `screen`
- owned base-game multiplayer assets that include `fileSysCheck.cfg` and
  `main/localized_*.iwd`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycod4serv create cod4server
```

Run setup:

```bash
alphagsm mycod4serv setup
```

Start it:

```bash
alphagsm mycod4serv start
```

Check it:

```bash
alphagsm mycod4serv status
```

Stop it:

```bash
alphagsm mycod4serv stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the official Linux dedicated-server archive
- still requires copied retail/localized multiplayer assets before the server
  can finish startup

`cod4server` is a bring-your-own-assets lane. AlphaGSM installs the Linux
dedicated binary for you, but the stock archive still does not include all of
the owned multiplayer files the server expects at startup.

Before `start`, copy the required owned files from a legitimate Call of Duty 4
installation into the AlphaGSM server tree:

```text
<install_dir>/fileSysCheck.cfg
<install_dir>/main/localized_*.iwd
```

Minimal operator flow:

```bash
alphagsm mycod4serv create cod4server
alphagsm mycod4serv setup
cp /path/to/cod4/fileSysCheck.cfg <install_dir>/
cp /path/to/cod4/main/localized_*.iwd <install_dir>/main/
alphagsm mycod4serv start
```

If the server still exits immediately, verify that `fileSysCheck.cfg` is at the
server root and the localized `.iwd` files are under `main/`, not only inside a
custom `moddir`.

## Useful Commands

```bash
alphagsm mycod4serv update
alphagsm mycod4serv backup
```

## Notes

- Module name: `cod4server`
- Default port: 28960
- Current blocker for anonymous installs: the default dedicated archive does
  not ship `fileSysCheck.cfg` or `main/localized_*.iwd`

## Developer Notes

### Run File

- **Executable**: `cod4_lnxded`
- **Location**: `<install_dir>/cod4_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Owned base assets still required**: `fileSysCheck.cfg`,
  `main/localized_*.iwd`
- **Copy targets before first start**: `<install_dir>/` for `fileSysCheck.cfg`,
  `<install_dir>/main/` for `localized_*.iwd`
- **Template**: See [server-templates/cod4server/](../server-templates/cod4server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/` (default `<install_dir>/main/`)
- **Workshop support**: No

## Mod Sources

Call of Duty 4 supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir`, tracks only the files it owns, and keeps the active `moddir` in the managed backup targets.

Examples:

```bash
alphagsm mycod4serv mod add url https://example.com/custom.pk3
alphagsm mycod4serv mod add url https://example.com/custom-pack.zip
alphagsm mycod4serv mod apply
alphagsm mycod4serv mod cleanup
```
