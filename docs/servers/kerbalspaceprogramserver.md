# Kerbal Space Program community

This guide covers the `kerbalspaceprogramserver` module in AlphaGSM.

`kerbalspaceprogramserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- Docker for the validated Linux runtime path
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mykerbalsp create kerbalspaceprogramserver
```

Run setup:

```bash
alphagsm mykerbalsp setup
```

Start it:

```bash
alphagsm mykerbalsp start
```

Check it:

```bash
alphagsm mykerbalsp status
```

Stop it:

```bash
alphagsm mykerbalsp stop
```

## Setup Details

Setup configures:

- the game port (default 8800)
- the install directory
- downloads and extracts the Linux LunaMultiplayer server archive
- prepares the first-run XML config files AlphaGSM manages before start

## Useful Commands

```bash
alphagsm mykerbalsp update
alphagsm mykerbalsp backup
```

## Notes

- Module name: `kerbalspaceprogramserver`
- Default port: 8800

## Developer Notes

### Run File

- **Executable**: `LMPServer-linux-x64/Server`
- **Location**: `<install_dir>/LMPServer-linux-x64/Server`
- **Runtime**: Native Linux, validated through the shared `steamcmd-linux` Docker runtime
- **Health surface**: generic `udp` on the managed main game port

### Server Configuration

- **Config files**:
  - `<install_dir>/LMPServer-linux-x64/Config/ConnectionSettings.xml`
  - `<install_dir>/LMPServer-linux-x64/Config/GeneralSettings.xml`
- AlphaGSM creates these files on first launch when the upstream archive has not generated them yet, then keeps the managed port, server name, and max players in sync before start.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
