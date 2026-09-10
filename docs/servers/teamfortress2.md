# Team Fortress 2-specific

This guide covers the `teamfortress2` module in AlphaGSM.

The checked-in support tracker currently marks the canonical Team Fortress 2
surface as `PASSED` on the documented Ubuntu 24.04 Linux baseline under the
`tf2` module id. `teamfortress2` is the package-backed canonical import
surface behind that validated TF2 server path.

## Requirements

The current AlphaGSM process integration requires Linux because it uses
`srcds_run` and Linux Steam client libraries. Setup rejects incompatible hosts
before downloading. Docker requires a Linux-container daemon, including when
Docker runs on a Windows desktop. Installation still uses the Linux SteamCMD
client on the manager host; run AlphaGSM itself in Linux or in the manager
container for this setup path.

- Optional `screen` or `tmux`; the subprocess backend is also available
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- For source installations, Python packages from `requirements-runtime.txt`

## Quick Start

Create the server:

```bash
alphagsm myteamfort create teamfortress2
```

Run setup:

```bash
alphagsm myteamfort setup
```

Start it:

```bash
alphagsm myteamfort start
```

Check it:

```bash
alphagsm myteamfort status
```

Stop it:

```bash
alphagsm myteamfort stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

The native TF2 config lives at `tf/cfg/server.cfg`. AlphaGSM keeps the
following values in sync through `set`:

- `set gamemap` aliases `map`, `startmap`, and `level`
- `set servername` updates the `hostname` entry in `server.cfg`
- `set rconpassword` updates `rcon_password`
- `set serverpassword` updates `sv_password`

Examples:

```bash
alphagsm myteamfort set gamemap --describe
alphagsm myteamfort set gamemap cp_dustbowl
alphagsm myteamfort set rconpassword secret
```

## Useful Commands

```bash
alphagsm myteamfort update
alphagsm myteamfort update -r
alphagsm myteamfort backup
```

`-r` restarts after the SteamCMD update. `-v` validates the files. See
[Updating Servers And AlphaGSM](../updating.md).

## Installing Mods

The supported path is AlphaGSM's checked-in `manifest` list. Add what you want,
then apply it. The full operator guide is
[Installing Mods](../installing-mods.md).

```bash
alphagsm myteamfort mod add manifest metamod
alphagsm myteamfort mod add manifest sourcemod
alphagsm myteamfort mod apply
alphagsm myteamfort mod list
```

`sourcemod` can be pinned to a registry channel such as `1.12`. `curated` is
still accepted as an alias for `manifest`. Files land under `tf/addons/` and
`tf/cfg/`. `mod cleanup` removes only AlphaGSM-owned addon files.

GameBanana and Mod DB ids/URLs are also accepted. Workshop `mod add` records a
desired item, but Workshop apply is still experimental for TF2 — prefer
`manifest`.

## Notes

- Module name: `teamfortress2`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `232250`

### Server Configuration

- **Config files**: `server.cfg`
- **Template**: See [server-templates/teamfortress2/](../server-templates/teamfortress2/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Curated mod directories**: `tf/addons` and `tf/cfg`
- **Curated mod examples**: `sourcemod`, `metamod`
- **Workshop support**: Experimental desired-state support only; apply/download is not yet verified
