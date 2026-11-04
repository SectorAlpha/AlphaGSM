# Starbound

This guide covers the `starbound` module in AlphaGSM.

`starbound` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that staged-native-server-tree prerequisite,
while local runs remain process-backed by default unless you opt into the
Docker backend.

## Requirements

- `screen`
- an owned Starbound install that provides `linux64/starbound_server` or
  `linux/starbound_server`, plus `assets/packed.pak`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`) when setup
  acquires the game
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystarboun create starbound
```

For an owned Steam copy, sign in once and let setup acquire app 211820:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm mystarboun setup --auth-profile owned
```

Enter credentials only at the local SteamCMD prompts. Anonymous SteamCMD can
log in to app 211820, but it mounts no depots and does not provide the Linux
server. A later setup that still has the saved profile keeps using that
profile so the empty anonymous install does not replace the owned files.
A local process run with an entitled profile downloaded the Linux tree,
launched `linux/starbound_server` (this build has no `linux64/starbound_server`),
and answered A2S on UDP 50333 (hostname AlphaGSM lastarbound, map `Unknown`,
0/8). The process was stopped and that UDP port was free. Docker was not run.

`starbound` is supported in `ENABLED (BYO)` mode. You can also stage a native
tree yourself. It needs `assets/packed.pak` and either
`linux64/starbound_server` or `linux/starbound_server`. A Windows executable
alone is not the Linux server.

Start it:

```bash
alphagsm mystarboun start
```

Check it:

```bash
alphagsm mystarboun status
```

Stop it:

```bash
alphagsm mystarboun stop
```

## Setup Details

Setup configures:

- the game port (default 21025)
- the install directory

Before each start, AlphaGSM writes `storage/starbound_server.config`. Stock
Starbound leaves `runQueryServer` false, so the UDP query socket never opens.
AlphaGSM sets `runQueryServer` to true and points `gameServerPort` and
`queryServerPort` at the game port. Game traffic is TCP and the Steam A2S
query is UDP on that same port. Non-interactive setup accepts an optional
port and otherwise keeps 21025:

```bash
alphagsm mystarboun setup -n 21025 /path/to/starbound
```

Change it later with `alphagsm <server-name> set port <port>` before start. Other settings
already in the file, including accounts and bans, are left in place. See
https://starbounder.org/Guide:Setting_Up_Multiplayer.

Suggested flow:

```bash
alphagsm mystarboun create starbound
alphagsm mystarboun setup --auth-profile owned -n 21025 /path/to/starbound
alphagsm mystarboun start
```

Manual staging uses the same port-then-directory order:

```bash
alphagsm mystarboun setup -n 21025 /path/to/starbound
# copy the Linux server binary, its runtime files, and assets/packed.pak into /path/to/starbound/
alphagsm mystarboun start
```

## Useful Commands

```bash
alphagsm mystarboun update
alphagsm mystarboun backup
```

## Notes

- Module name: `starbound`
- Default port: 21025 (TCP game, UDP A2S query)
- A2S requires `runQueryServer` true: https://starbounder.org/Guide:Setting_Up_Multiplayer

<!-- alphagsm-server-variables:start -->

## Server variables

After `create starbound`, inspect or change these with `set`:

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

- **Executable**: `linux64/starbound_server`, or `linux/starbound_server` when that is the owned Linux build
- **Location**: beside `sbinit.config` in `<install_dir>/linux64/` or `<install_dir>/linux/`
- **Working directory**: the directory that contains the selected binary
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `211820` (authentication required; anonymous mounts no depots)

### Server Configuration

- **Config file**: `<install_dir>/storage/starbound_server.config`
- **Template**: See [server-templates/starbound/](../server-templates/starbound/) if available
- **Query**: Steam A2S on the game port after `runQueryServer` is true

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
The preferred Steam-owned path is `alphagsm steam-auth login owned <username>`,
then `alphagsm <server-name> setup --auth-profile owned`. Setup remembers the
profile name and fetches app 211820 before installing. The managed import keeps
`assets/packed.pak` and the Linux dedicated binary (`linux64/starbound_server`
or `linux/starbound_server`) with the Linux runtime files beside it. It does
not treat a Windows executable as the Linux server. Direct file acquisition
remains available through `assets fetch steam-owned --auth-profile owned`.
See [BYO files and private SteamCMD acquisition](../byo-files.md).
