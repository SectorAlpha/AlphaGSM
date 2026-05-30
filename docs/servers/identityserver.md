# Identity

This guide covers the `identityserver` module in AlphaGSM.

## Requirements

- `screen`
- either a direct Identity server archive URL or a pre-staged Identity server tree
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

`identityserver` is supported in `ENABLED (BYO)` mode. Before `setup` or
`start`, either:

- set `url` to a direct Identity server archive, or
- stage `IdentityServer.x86_64` and the rest of the Identity server files
  inside your chosen `<install_dir>/`

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
- downloads and extracts the server archive when `url` is set

Suggested flow:

```bash
alphagsm myidentity create identityserver
alphagsm myidentity set url https://example.invalid/identity-server.zip
alphagsm myidentity setup -n 7777 /path/to/identityserver
alphagsm myidentity start
```

Or, if you already have the server files:

```bash
alphagsm myidentity create identityserver
alphagsm myidentity setup -n 7777 /path/to/identityserver
# copy IdentityServer.x86_64 and the rest of the server tree into /path/to/identityserver/
alphagsm myidentity start
```

## Useful Commands

```bash
alphagsm myidentity update
alphagsm myidentity backup
alphagsm myidentity set url https://example.invalid/identity-server.zip
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
