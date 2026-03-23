# Mumble

This guide covers the `mumbleserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

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

- **Executable**: See game module source
- **Engine**: Custom

### Server Configuration

- **Config files**: `mumble-server.ini`
- **Template**: See [server-templates/mumbleserver/](../server-templates/mumbleserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
