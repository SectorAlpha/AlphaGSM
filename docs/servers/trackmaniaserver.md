# Trackmania

This guide covers the `trackmaniaserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytrackman create trackmaniaserver
```

Run setup:

```bash
alphagsm mytrackman setup
```

Start it:

```bash
alphagsm mytrackman start
```

Check it:

```bash
alphagsm mytrackman status
```

Stop it:

```bash
alphagsm mytrackman stop
```

## Setup Details

Setup configures:

- the XML-RPC port (default 5000)
- the install directory
- downloads and extracts the server archive
- syncs `GameData/Config/dedicated_cfg.txt` so the dedicated server listens on the configured XML-RPC port

## Useful Commands

```bash
alphagsm mytrackman update
alphagsm mytrackman backup
```

## Notes

- Module name: `trackmaniaserver`
- Default XML-RPC port: `5000`
- `query`, `info`, and `info --json` report TCP reachability on the XML-RPC endpoint rather than A2S game-server metadata

## Developer Notes

### Run File

- **Executable**: `TrackmaniaServer`
- **Location**: `<install_dir>/TrackmaniaServer`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<install_dir>/GameData/Config/dedicated_cfg.txt`
- **Template**: See [server-templates/trackmaniaserver/](../server-templates/trackmaniaserver/) if available

AlphaGSM rewrites `<xmlrpc_port>` in `dedicated_cfg.txt` during setup and before each start so the configured AlphaGSM port and the live Trackmania XML-RPC listener stay aligned.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
