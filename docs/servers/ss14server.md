# Space Station 14

This guide covers the `ss14server` module in AlphaGSM.

`ss14server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. AlphaGSM supports the complete `Robust.Server` lifecycle through
both the process and Docker runtimes, but the official Wizard's Den build feed
currently publishes no server builds. Supply a direct Linux x64 server archive
URL until that feed resumes.

## Requirements

- a direct Linux x64 Space Station 14 server archive URL
- process runtime: `screen` and a host-installed `.NET 10` runtime (`dotnet`)
- Docker runtime: Docker; the shared runtime image supplies the server runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myss14serv create ss14server
```

Run setup:

```bash
alphagsm myss14serv setup --url https://example.invalid/ss14-server-linux-x64.zip
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
- downloads and extracts the operator-supplied server archive
- writes the managed `server_config.toml`
- enables the built-in HTTP status endpoint AlphaGSM uses for `query` and `info`
- launches `Robust.Server` through the selected process or Docker runtime

## Useful Commands

```bash
alphagsm myss14serv update
alphagsm myss14serv backup
```

## Notes

- Module name: `ss14server`
- Default port: 1212
- `setup` without `--url` will automatically use the official Wizard's Den
  build feed again when that feed publishes server builds.
- GitHub integration and smoke coverage accept
  `ALPHAGSM_SS14_SERVER_URL` to validate a supplied archive end to end.

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
