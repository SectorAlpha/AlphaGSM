# MX Bikes

This guide covers the `mxbikesserver` module in AlphaGSM.

`mxbikesserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that user-supplied-archive
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- A direct MX Bikes dedicated-server archive URL supplied by the operator
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymxbikess create mxbikesserver
```

Run setup:

```bash
alphagsm mymxbikess setup
```

Start it:

```bash
alphagsm mymxbikess start
```

Check it:

```bash
alphagsm mymxbikess status
```

Stop it:

```bash
alphagsm mymxbikess stop
```

## Setup Details

Setup configures:

- the game port (default 54210)
- the install directory
- downloads and extracts the server archive

MX Bikes is supported in `ENABLED (BYO)` mode in AlphaGSM. Before
`setup`, provide a direct archive URL for the dedicated server, for example by
running `alphagsm mymxbikess set url <https://.../mxbikes-dedicated.zip>` or
passing the URL during setup.

## Useful Commands

```bash
alphagsm mymxbikess update
alphagsm mymxbikess backup
alphagsm mymxbikess set url https://example.invalid/mxbikes-dedicated.zip
```

## Notes

- Module name: `mxbikesserver`
- Default port: 54210

<!-- alphagsm-server-variables:start -->

## Server variables

After `create mxbikesserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `mxbikes_dedicated`
- **Location**: `<install_dir>/mxbikes_dedicated`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/mxbikesserver/](../server-templates/mxbikesserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
