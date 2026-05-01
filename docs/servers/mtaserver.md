# Multi Theft Auto

This guide covers the `mtaserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymtaserve create mtaserver
```

Run setup:

```bash
alphagsm mymtaserve setup
```

Start it:

```bash
alphagsm mymtaserve start
```

Check it:

```bash
alphagsm mymtaserve status
```

Stop it:

```bash
alphagsm mymtaserve stop
```

## Setup Details

Setup configures:

- the game port (default 22003)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mymtaserve update
alphagsm mymtaserve backup
```

## Mod Sources

Multi Theft Auto resource management uses the standard resource tree under
`mods/deathmatch/resources/`.

- AlphaGSM stores MTA mod cache/state under `.alphagsm/mods/mtaserver/`.
- Current mod source support is `manifest`/`curated`, `url`, and `community`.
- `manifest` installs checked-in MTA resource families from immutable release archives. The current built-in families are `pattach`, `chat2`, and `animationspanel`.
- `url` accepts direct archive URLs for resource packs when the archive exposes either `mods/deathmatch/resources/<name>/...`, a top-level resource directory that contains `meta.xml`, or a resource archive whose root itself contains `meta.xml`.
- `community` accepts canonical MTA community detail page URLs such as `https://community.multitheftauto.com/index.php?p=resources&s=details&id=<id>` and follows the upstream cookie-backed download flow automatically.
- AlphaGSM records installed resource files per entry so `mod cleanup` removes only tracked resources and leaves unrelated resources alone.

Examples:

```bash
alphagsm mymtaserve mod add manifest pattach
alphagsm mymtaserve mod add url https://resources.example.invalid/coolrace.zip
alphagsm mymtaserve mod add community https://community.multitheftauto.com/index.php?p=resources&s=details&id=19052
alphagsm mymtaserve mod apply
alphagsm mymtaserve mod cleanup
```

Some resources still need normal MTA-side enablement or configuration after
installation, such as adding them to `mtaserver.conf`, granting ACL rights, or
starting the resource in-game.

## Notes

- Module name: `mtaserver`
- Default port: 22003

## Developer Notes

### Run File

- **Executable**: `mta-server64`
- **Location**: `<install_dir>/mta-server64`
- **Engine**: Custom

### Server Configuration

- **Config file**: `mods/deathmatch/mtaserver.conf`
- **Template**: See [server-templates/mtaserver/](../server-templates/mtaserver/) if available

### Maps and Mods

- **Map directory**: `mods/deathmatch/resources/`
- **Mod directory**: `mods/deathmatch/resources/`
- **Workshop support**: No
