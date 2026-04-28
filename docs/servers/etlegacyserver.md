# ET: Legacy

This guide covers the `etlegacyserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myetlegacy create etlegacyserver
```

Run setup:

```bash
alphagsm myetlegacy setup
```

Start it:

```bash
alphagsm myetlegacy start
```

Check it:

```bash
alphagsm myetlegacy status
```

Stop it:

```bash
alphagsm myetlegacy stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myetlegacy update
alphagsm myetlegacy backup
alphagsm myetlegacy set servername "AlphaGSM ET"
alphagsm myetlegacy set port 27961
```

`set servername` and `set port` rewrite `etl_server.cfg` immediately through the schema-backed config-sync path.

## Notes

- Module name: `etlegacyserver`
- Default port: 27960

## Developer Notes

### Run File

- **Executable**: `etlded.x86_64`
- **Location**: `<install_dir>/etlded.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: `etl_server.cfg`
- **Template**: See [server-templates/etlegacyserver/](../server-templates/etlegacyserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `sv_hostname` and `net_port` aligned with `set`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
