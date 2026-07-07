# Skyrim Together Reborn

This guide covers the `skyrimtogetherrebornserver` module in AlphaGSM.

`skyrimtogetherrebornserver` is currently `ENABLED (BYO)` on the documented
Ubuntu 24.04 Linux baseline. The current GitHub integration lane still
exercises both process and Docker runtime selection around that
direct-archive-or-staged-tree prerequisite, while local runs remain
process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- either a direct Skyrim Together Reborn server archive URL or a pre-staged
  Skyrim Together Reborn server tree
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myskyrimto create skyrimtogetherrebornserver
```

Run setup:

```bash
alphagsm myskyrimto setup
```

`skyrimtogetherrebornserver` is supported in `ENABLED (BYO)` mode. Before
`setup` or `start`, either:

- set `url` to a working Skyrim Together Reborn server archive, or
- stage `SkyrimTogetherServer` and the rest of the server files inside your
  chosen `<install_dir>/`

Start it:

```bash
alphagsm myskyrimto start
```

Check it:

```bash
alphagsm myskyrimto status
```

Stop it:

```bash
alphagsm myskyrimto stop
```

## Setup Details

Setup configures:

- the game port (default 10578)
- the install directory
- downloads and extracts the server archive when `url` is set

Suggested flow:

```bash
alphagsm myskyrimto create skyrimtogetherrebornserver
alphagsm myskyrimto set url https://example.invalid/skyrimtogether-server.zip
alphagsm myskyrimto setup -n 10578 /path/to/skyrimtogether
alphagsm myskyrimto start
```

Or, if you already have the server files:

```bash
alphagsm myskyrimto create skyrimtogetherrebornserver
alphagsm myskyrimto setup -n 10578 /path/to/skyrimtogether
# copy SkyrimTogetherServer and the rest of the server tree into /path/to/skyrimtogether/
alphagsm myskyrimto start
```

## Useful Commands

```bash
alphagsm myskyrimto update
alphagsm myskyrimto backup
alphagsm myskyrimto set url https://example.invalid/skyrimtogether-server.zip
```

## Notes

- Module name: `skyrimtogetherrebornserver`
- Default port: 10578

## Developer Notes

### Run File

- **Executable**: `SkyrimTogetherServer`
- **Location**: `<install_dir>/SkyrimTogetherServer`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/skyrimtogetherrebornserver/](../server-templates/skyrimtogetherrebornserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
