# Trackmania

This guide covers the `trackmaniaserver` module in AlphaGSM.

`trackmaniaserver` is currently `PASSED` in the checked-in support tracker on
the documented Ubuntu 24.04 Linux baseline. The current GitHub integration
lane validates both process and Docker runtimes for this module, while local
runs remain process-backed by default unless you opt into the Docker backend.

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

<!-- alphagsm-server-variables:start -->

## Server variables

After `create trackmaniaserver`, inspect or change these with `set`:

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
