# Mumble

This guide covers the `mumbleserver` module in AlphaGSM.

`mumbleserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. GitHub keeps one Docker-default lifecycle through the shared
`simple-tcp` runtime. Process mode remains available when an operator has a
host `mumble-server` or `murmurd` package installed.

## Requirements

- `docker` for the tested anonymous support path
- Python packages from `requirements.txt`

If you already have a host `mumble-server` or `murmurd` package installed, the process runtime can still launch it directly. The validated anonymous AlphaGSM path uses the shared Docker runtime image instead.

## Quick Start

Create the server:

```bash
alphagsm mymumblese create mumbleserver
```

Run setup:

```bash
alphagsm mymumblese setup
```

Start it:

```bash
alphagsm mymumblese start
```

Check it:

```bash
alphagsm mymumblese status
```

Stop it:

```bash
alphagsm mymumblese stop
```

## Setup Details

Setup configures:

- the game port (default 64738)
- the install directory
- the managed `mumble-server.ini` config file used by either the host package or the Docker runtime image

Common `set` values:

```bash
alphagsm mymumblese set maxplayers 100
alphagsm mymumblese set serverpassword voice-secret
alphagsm mymumblese set welcometext "Welcome to AlphaGSM Mumble"
```

## Useful Commands

```bash
alphagsm mymumblese update
alphagsm mymumblese backup
```

## Notes

- Module name: `mumbleserver`
- Default port: 64738

## Developer Notes

### Run File

- **Executable**: `mumble-server` / `murmurd`
- **Engine**: Mumble / Murmur
- **Validated runtime**: Docker backend with `ghcr.io/sectoralpha/alphagsm-simple-tcp-runtime:latest`

### Server Configuration

- **Config files**: `mumble-server.ini`
- **Template**: See [server-templates/mumbleserver/](../server-templates/mumbleserver/) if available

### Query And Info

- `alphagsm mymumblese query` uses TCP reachability on the configured voice port
- `alphagsm mymumblese info --json` reports protocol `tcp`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
