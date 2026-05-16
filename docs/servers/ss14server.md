# Space Station 14

This guide covers the `ss14server` module in AlphaGSM.

## Requirements

- `screen`
- host-installed `.NET 10` runtime (`dotnet`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myss14serv create ss14server
```

Run setup:

```bash
alphagsm myss14serv setup
```

Start it:

```bash
alphagsm myss14serv start
```

Check it:

```bash
alphagsm myss14serv status
```

Stop it:

```bash
alphagsm myss14serv stop
```

## Setup Details

Setup configures:

- the game port (default 1212)
- the install directory
- downloads and extracts the server archive
- writes the managed `server_config.toml`
- enables the built-in HTTP status endpoint AlphaGSM uses for `query` and `info`
- launches `Robust.Server`, which requires the host `.NET` runtime

## Useful Commands

```bash
alphagsm myss14serv update
alphagsm myss14serv backup
```

## Notes

- Module name: `ss14server`
- Default port: 1212

## Developer Notes

### Run File

- **Executable**: `Robust.Server`
- **Location**: `<install_dir>/Robust.Server`
- **Engine**: Custom

### Server Configuration

- **Config files**: `server_config.toml`
- **Template**: See [server-templates/ss14server/](../server-templates/ss14server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
