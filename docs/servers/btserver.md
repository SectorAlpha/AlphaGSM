# Barotrauma

This guide covers the `btserver` module in AlphaGSM.

`btserver` is currently `PASSED` in the checked-in support tracker. On the
documented Ubuntu 24.04 Linux baseline, the current smoke and GitHub
integration coverage runs through the shared `steamcmd-linux` Docker runtime,
while local host-process flows remain the fallback path documented elsewhere
in the repo. AlphaGSM checks Barotrauma through the live Lidgren UDP surface
on the primary game port rather than assuming the adjacent Steam query port
provides A2S.

## Requirements

- Docker for the validated Linux runtime path
- Python 3 inside the Docker image for Barotrauma's native console terminal;
  the checked-in `steamcmd-linux` image includes it
- For process mode: `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybtserver create btserver
```

Run setup:

```bash
alphagsm mybtserver setup
```

Start it:

```bash
alphagsm mybtserver start
```

Check it:

```bash
alphagsm mybtserver status
```

Stop it:

```bash
alphagsm mybtserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the adjacent query port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

Native XML Workshop packages use anonymous SteamCMD access; no Steam account is
required. Item and collection identifiers accept numeric IDs or Steam Community URLs.

```bash
alphagsm mybtserver mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=2499918466
alphagsm mybtserver mod add workshop-collection COLLECTION_ID_OR_URL
alphagsm mybtserver mod list
alphagsm mybtserver mod apply
alphagsm mybtserver mod remove workshop 2499918466
alphagsm mybtserver mod apply
alphagsm mybtserver mod cleanup
```

Apply validates and downloads packages, stages owned files under
`LocalMods/alphagsm-ID`, and enables their package names and file lists in
`config_player.xml`. Start and update reapply desired state by default. Restart a
running server after changing its mods. Existing operator settings and package
entries are preserved. Cleanup clears desired items and removes only unchanged
AlphaGSM-owned payloads and native entries; externally edited owned content causes
a clear refusal. The download cache remains available.

This supports native regular XML packages, including multiplayer item and
submarine content. Core replacements and Lua/CSharp packages needing a separate
server executable require manual configuration. A configured package is reported
as configured; the engine must load it before it is usable.

Set `ALPHAGSM_RUN_WORKSHOP=1` when running `run_btserver.sh` to check the public
[BaroCraftables fixture](https://steamcommunity.com/sharedfiles/filedetails/?id=2499918466)
through native enabled-package hashes and its loaded Welding Table prefab. On
13 October 2026, both process and Docker opt-in integration cases passed with
these engine checks, CLI health commands and complete shutdown.

```bash
alphagsm mybtserver update
alphagsm mybtserver backup
```

## Notes

- Module name: `btserver`
- Default game port: 27015
- Default query port: 27016
- `query`, `info`, and `info --json` use generic UDP health on the managed
  game port for both process and Docker.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create btserver`, inspect or change these with `set`:

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

- **Executable**: `DedicatedServer`
- **Location**: `<install_dir>/DedicatedServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1026340`

### Server Configuration

- **Config files**: `config_player.xml`, `serversettings.xml`
- **Max players**: `16`
- **Template**: See [server-templates/btserver/](../server-templates/btserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: Native regular XML packages through `mod`
