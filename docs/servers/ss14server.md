# Space Station 14

This guide covers the `ss14server` module in AlphaGSM.

`ss14server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. Setup downloads the current Wizard's Den linux-x64 `Robust.Server`
build. Pass `--url` for another direct Linux x64 archive. A local process
lifecycle answered the Robust status API and stopped cleanly. Docker was not
rerun in that check.

## Requirements

- network access to the Wizard's Den build feed, or a direct Linux x64 archive URL
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
alphagsm myss14serv setup
# or: alphagsm myss14serv setup --url https://example.invalid/ss14-server-linux-x64.zip
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
- downloads and extracts the Wizard's Den linux-x64 build, or the archive from `--url`
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
- `setup` without `--url` uses the current Wizard's Den linux-x64 server build.
- Local process query and info used `robust_status` and reported
  `max_players` from the server's `soft_max_players` value. Docker was not rerun.
- GitHub integration and smoke coverage accept
  `ALPHAGSM_SS14_SERVER_URL` to validate a supplied archive end to end.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ss14server`, inspect or change these with `set`:

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

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
This helper checks known sentinels only and directs you to stage the complete
compatible distribution manually; managed import is unavailable for this recipe.
See [BYO files and private SteamCMD acquisition](../byo-files.md).
