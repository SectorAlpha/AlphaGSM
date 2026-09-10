# Valheim

This guide covers the `valheim` module in AlphaGSM.

`valheim` is currently `PASSED` in the checked-in support tracker. On the
documented Ubuntu 24.04 Linux baseline, the current smoke and GitHub
integration coverage runs through the shared `steamcmd-linux` Docker runtime,
while local host-process flows remain the fallback path documented elsewhere
in the repo. Query/info use the live primary UDP game-port surface rather than
requiring a stale A2S response.

## Requirements

- Docker for the validated Linux runtime path
- For process mode: `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Runtime libraries `libatomic1`, `libpulse0`, and `libpulse-dev`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvalheim create valheim
```

Run setup:

```bash
alphagsm myvalheim setup
```

Start it:

```bash
alphagsm myvalheim start
```

Check it:

```bash
alphagsm myvalheim status
```

Stop it:

```bash
alphagsm myvalheim stop
```

## Setup Details

Setup configures:

- the game port (default 2456)
- the adjacent server port (default 2457)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myvalheim update
alphagsm myvalheim backup
```

## Notes

- Module name: `valheim`
- Default port: 2456
- Network protocol: UDP; Docker publishes the primary and adjacent ports
- Readiness marker: `Game server connected`
- `query`, `info`, and `info --json` use generic UDP health on the primary
  game port

<!-- alphagsm-server-variables:start -->

## Server variables

After `create valheim`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `serverpassword` | sv_password, password | string | Password required to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `valheim_server.x86_64`
- **Location**: `<install_dir>/valheim_server.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `896660`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/valheim/](../server-templates/valheim/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
