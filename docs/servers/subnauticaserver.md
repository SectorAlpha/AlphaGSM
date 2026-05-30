# Subnautica community

This guide covers the `subnauticaserver` module in AlphaGSM.

## Requirements

- `screen`
- An owned Subnautica client installation path for Nitrox to inspect
  - Nitrox currently looks for a configured game path or the `SUBNAUTICA_INSTALLATION_PATH` environment variable
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysubnauti create subnauticaserver
```

Run setup:

```bash
alphagsm mysubnauti setup
```

Start it:

```bash
alphagsm mysubnauti start
```

Check it:

```bash
alphagsm mysubnauti status
```

Stop it:

```bash
alphagsm mysubnauti stop
```

## Setup Details

Setup configures:

- the game port (default 11000)
- the install directory
- downloads and extracts the server archive

This server is supported in `ENABLED (BYO)` mode. Before `start`, provide Nitrox with a real owned Subnautica installation path.
On the current Linux lane, the missing `.NET` runtime is no longer the blocker;
startup now aborts only when Nitrox cannot find the base game files.

## Useful Commands

```bash
alphagsm mysubnauti update
alphagsm mysubnauti backup
```

## Notes

- Module name: `subnauticaserver`
- Default port: 11000

## Developer Notes

### Run File

- **Executable**: `Nitrox.Server.Subnautica`
- **Location**: `<install_dir>/Nitrox.Server.Subnautica`
- **Engine**: Custom
- **Owned client path required before start**: set Nitrox's game path or `SUBNAUTICA_INSTALLATION_PATH` to a real Subnautica install

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/subnauticaserver/](../server-templates/subnauticaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
