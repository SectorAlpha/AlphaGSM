# Identity

This guide covers the `identityserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myidentity create identityserver
```

Run setup:

```bash
alphagsm myidentity setup
```

Start it:

```bash
alphagsm myidentity start
```

Check it:

```bash
alphagsm myidentity status
```

Stop it:

```bash
alphagsm myidentity stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myidentity update
alphagsm myidentity backup
```

## Notes

- Module name: `identityserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `IdentityServer.x86_64`
- **Location**: `<install_dir>/IdentityServer.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/identityserver/](../server-templates/identityserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
