# Return to Castle Wolfenstein

This guide covers the `rtcwserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

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

## Useful Commands

```bash
alphagsm myrtcwserv update
alphagsm myrtcwserv backup
```

## Notes

- Module name: `rtcwserver`
- Default port: 27960

## Developer Notes

### Run File

- **Executable**: `iowolfded.x86_64`
- **Location**: `<install_dir>/iowolfded.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set fs_game`, and `set map` rewrite `<fs_game>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/rtcwserver/](../server-templates/rtcwserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
