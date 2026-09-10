# Dark and Light

This guide covers the `darkandlightserver` module in AlphaGSM.

`darkandlightserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The validated Linux lifecycle uses the shared Docker `wine-proton` runtime. Current host-process Proton starts stay alive without opening the managed UDP health surface, so GitHub CI does not claim process-runtime support for this module.

## Requirements

- Docker
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydarkandl create darkandlightserver
```

Run setup:

```bash
alphagsm mydarkandl setup
```

Start it:

```bash
alphagsm mydarkandl start
```

Check it:

```bash
alphagsm mydarkandl status
```

Stop it:

```bash
alphagsm mydarkandl stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27016)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mydarkandl update
alphagsm mydarkandl backup
```

## Notes

- Module name: `darkandlightserver`
- Default game port: 7777
- Default query port: 27016
- Current validation status: PASSED 2026-05-30. Fresh smoke and integration
  now both pass on the Docker-backed Linux `wine-proton` runtime once AlphaGSM
  launches Dark and Light through the shared in-container Xvfb/software-GL
  path, treats the live health surface as generic `udp` on the managed main
  game port, and routes stop through the shared runtime layer instead of
  depending on a host `screen` console session or the older stale `queryport`
  A2S assumption.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create darkandlightserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `adminpassword` | adminpass | string | Server admin password. Stored as a secret. |
| `serverpassword` | sv_password, password | string | Password required to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `DNL/Binaries/Win64/DNLServer.exe`
- **Location**: `<install_dir>/DNL/Binaries/Win64/DNLServer.exe`
- **Engine**: UE4 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `630230`

The validated Linux path now runs through AlphaGSM's Docker-backed
`wine-proton` runtime image rather than a host `screen` session. The current
checked-in smoke and integration coverage prove the live contract on the
managed main game port: `query`, `info`, and `info --json` all succeed as
generic `udp` once the containerized Xvfb/software-GL environment brings the
Windows dedicated server up cleanly. The historical `queryport` `27016` A2S
assumption is no longer part of the supported readiness contract on Linux.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/darkandlightserver/](../server-templates/darkandlightserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
