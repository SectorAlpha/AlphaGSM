# GRAV

This guide covers the `gravserver` module in AlphaGSM.

`gravserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that staged-server prerequisite,
while local runs remain process-backed by default unless you opt into the
Docker backend.

## Requirements

- `screen`
- an owned GRAV dedicated server tree staged locally
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygravserv create gravserver
```

Run setup:

```bash
alphagsm mygravserv setup
```

GRAV is supported in `ENABLED (BYO)` mode in AlphaGSM. Before `setup` or
`start`, copy an owned GRAV dedicated server tree into your chosen
`<install_dir>/` so the executable
`<install_dir>/CAGGameServer-Win32-Shipping` exists.

Start it:

```bash
alphagsm mygravserv start
```

Check it:

```bash
alphagsm mygravserv status
```

Stop it:

```bash
alphagsm mygravserv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory

Suggested flow:

```bash
alphagsm mygravserv create gravserver
alphagsm mygravserv setup -n 7777 /path/to/gravserver
# copy the owned GRAV dedicated server files into /path/to/gravserver/
alphagsm mygravserv start
```

## Useful Commands

```bash
alphagsm mygravserv update
alphagsm mygravserv backup
```

## Notes

- Module name: `gravserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `CAGGameServer-Win32-Shipping`
- **Location**: `<install_dir>/CAGGameServer-Win32-Shipping`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/gravserver/](../server-templates/gravserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
