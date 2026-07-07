# San Andreas Multiplayer

This guide covers the `sampserver` module in AlphaGSM.

`sampserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that direct-archive-or-staged-tree
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- either a direct SA-MP dedicated-server archive URL or a pre-staged SA-MP
  Linux server tree
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysampserv create sampserver
```

Run setup:

```bash
alphagsm mysampserv setup
```

`sampserver` is supported in `ENABLED (BYO)` mode. Before `setup` or `start`,
either:

- set `url` to a working SA-MP dedicated-server archive, or
- stage `samp03svr` and the rest of the SA-MP server files inside your chosen
  `<install_dir>/`

Start it:

```bash
alphagsm mysampserv start
```

Check it:

```bash
alphagsm mysampserv status
```

Stop it:

```bash
alphagsm mysampserv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive when `url` is set

Suggested flow:

```bash
alphagsm mysampserv create sampserver
alphagsm mysampserv set url https://example.invalid/samp-server.tar.gz
alphagsm mysampserv setup -n 7777 /path/to/samp
alphagsm mysampserv start
```

Or, if you already have the server files:

```bash
alphagsm mysampserv create sampserver
alphagsm mysampserv setup -n 7777 /path/to/samp
# copy samp03svr and the rest of the server tree into /path/to/samp/
alphagsm mysampserv start
```

## Useful Commands

```bash
alphagsm mysampserv update
alphagsm mysampserv backup
alphagsm mysampserv set url https://example.invalid/samp-server.tar.gz
```

## Notes

- Module name: `sampserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `samp03svr`
- **Location**: `<install_dir>/samp03svr`
- **Engine**: Custom

### Server Configuration

- **Config files**: `server.cfg`
- **Template**: See [server-templates/sampserver/](../server-templates/sampserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
