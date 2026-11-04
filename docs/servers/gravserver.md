# GRAV

This guide covers the `gravserver` module in AlphaGSM.

`gravserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that staged-server prerequisite,
while local runs remain process-backed by default unless you opt into the
Docker backend.

## Requirements

- `screen`
- an owned GRAV dedicated server tree staged locally
- On Linux, Wine and `xvfb-run`. The dedicated server is the Win32 build shipped inside the owned Steam game (app 332500). There is no separate Linux dedicated-server archive. Anonymous SteamCMD does not mount a depot. A local process start with a saved profile answered A2S on UDP 41002 (hostname `lagrav`, map `Reborn Update 9.8.1`, 0/255). The game port was 41000 and the peer port was 41001. The process was stopped and those UDP ports were free. Docker was not run. The default query port 27015 was already taken.
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygravserv create gravserver
```

Run setup:

```bash
alphagsm mygravserv setup
```

GRAV is supported in `ENABLED (BYO)` mode in AlphaGSM. Before `setup` or
`start`, stage an owned GRAV Windows tree so
`<install_dir>/Binaries/Win32/CAGGameServer-Win32-Shipping.exe` exists.
AlphaGSM also accepts `CAGGameServer-Win32-Shipping` at the install root.

Start it:

```bash
alphagsm mygravserv start
```

Check it:

```bash
alphagsm mygravserv status
```

Stop it:

```bash
alphagsm mygravserv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory

Suggested flow:

```bash
alphagsm mygravserv create gravserver
alphagsm mygravserv setup -n 7777 /path/to/gravserver
# stage the owned Steam tree, including Binaries/Win32/CAGGameServer-Win32-Shipping.exe
alphagsm mygravserv start
```

## Useful Commands

```bash
alphagsm mygravserv update
alphagsm mygravserv backup
```

## Notes

- Module name: `gravserver`
- Default game port: 7777
- Default peer port: 7778
- `query` and `info` use Steam A2S on the dedicated `queryport` (default 27015), not the game port.
- Linux launches `Binaries/Win32/CAGGameServer-Win32-Shipping.exe` from `Binaries/` with Wine under Xvfb (`prefer_proton` is off). The Docker runtime family stays `steamcmd-linux`.
- SteamCMD app 332500 is the owned GRAV install. Anonymous login may mount no depot. A saved Steam auth profile is passed to SteamCMD only when `steam_auth_profile` is set, and that session does not fall back to anonymous.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create gravserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `adminpassword` | adminpass | string | Server admin password. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `CAGGameServer-Win32-Shipping.exe`
- **Location**: `<install_dir>/Binaries/Win32/CAGGameServer-Win32-Shipping.exe`
- **Working directory**: `<install_dir>/Binaries/`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/gravserver/](../server-templates/gravserver/) if available

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
