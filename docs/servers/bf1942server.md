# Battlefield 1942

This guide covers the `bf1942server` module in AlphaGSM.

`bf1942server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that archive-or-staged-tree
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- either a direct Battlefield 1942 dedicated-server archive URL or a pre-staged
  Battlefield 1942 Linux dedicated server tree
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybf1942se create bf1942server
```

Run setup:

```bash
alphagsm mybf1942se setup
```

`bf1942server` is supported in `ENABLED (BYO)` mode. Before `setup` or
`start`, either:

- set `url` to a working Battlefield 1942 dedicated-server archive, or
- stage `bf1942_lnxded` and the rest of the Battlefield 1942 server files
  inside your chosen `<install_dir>/`

Start it:

```bash
alphagsm mybf1942se start
```

Check it:

```bash
alphagsm mybf1942se status
```

Stop it:

```bash
alphagsm mybf1942se stop
```

## Setup Details

Setup configures:

- the game port (default 1942)
- the install directory
- downloads and extracts the server archive when `url` is set

Suggested flow:

```bash
alphagsm mybf1942se create bf1942server
alphagsm mybf1942se set url https://example.invalid/bf1942-dedicated.tar.gz
alphagsm mybf1942se setup -n 1942 /path/to/bf1942
alphagsm mybf1942se start
```

Or, if you already have the server files:

```bash
alphagsm mybf1942se create bf1942server
alphagsm mybf1942se setup -n 1942 /path/to/bf1942
# copy bf1942_lnxded and the rest of the server tree into /path/to/bf1942/
alphagsm mybf1942se start
```

## Useful Commands

```bash
alphagsm mybf1942se update
alphagsm mybf1942se backup
alphagsm mybf1942se set url https://example.invalid/bf1942-dedicated.tar.gz
```

## Notes

- Module name: `bf1942server`
- Default port: 1942

## Developer Notes

### Run File

- **Executable**: `bf1942_lnxded`
- **Location**: `<install_dir>/bf1942_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/bf1942server/](../server-templates/bf1942server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
