# counterstrike2

This guide covers the `counterstrike2` module in AlphaGSM.

`counterstrike2` is currently `PASSED` in the checked-in support tracker on
the documented Ubuntu 24.04 Linux baseline. Use this module (or its
`cs2server` alias) for the current CS2 dedicated-server flow; the legacy
`counterstrikeglobaloffensive` / `csgo` surface remains a separate disabled
app `740` path.

```bash
alphagsm myserver create counterstrike2
```

`cs2server` is an alias for this module.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycs2 create counterstrike2
```

Run setup:

```bash
alphagsm mycs2 setup
```

Start it:

```bash
alphagsm mycs2 start
```

Check it:

```bash
alphagsm mycs2 status
```

Stop it:

```bash
alphagsm mycs2 stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files for Steam app `730`
- the launcher defaults to `game/cs2.sh`
- Source config is written under `game/csgo/cfg/server.cfg`

CI's anonymous app `730` install downloaded 73.4 GB and took about 22 minutes
20 seconds in the successful
[smoke run on 2026-10-15](https://github.com/SectorAlpha/AlphaGSM/actions/runs/38775144746).
Integration setup now
allows one bounded hour for that download. A timeout fails the test and retains
captured output, bounded Steam content-log tails, download counters and free
disk space; it no longer starts a short retry against a possibly active
SteamCMD child or reports a timeout as a skip. Both runtime installs completed
in [run 38812335342](https://github.com/SectorAlpha/AlphaGSM/actions/runs/38812335342),
revealing separate readiness and bot-population failures. This lifecycle has its own
outer test deadline covering setup, readiness waits, shutdown and
command overhead, so the ordinary 20-minute integration default cannot abort
the download first.

Disposable smoke and integration installs now write
`game/csgo/cfg/gamemode_competitive_server.cfg` with `bot_quota 0`, `bot_kick`
and `sv_hibernate_when_empty 0`. CS2 executes game-mode defaults after
`server.cfg`; the native override keeps the test empty and awake after those
defaults. See [Valve's game-mode configuration order](https://developer.valvesoftware.com/wiki/Counter-Strike:_Global_Offensive/Game_Modes).
These rules apply to the temporary test installation. Operator configuration
is unchanged. Integration readiness requires real A2S and AlphaGSM info responses,
including `de_dust2`, the managed port, and zero players/bots, rather than
depending on Source 1 startup log strings. Replacement CI validation is pending.

## Notes

- Module name: `counterstrike2`
- Default port: 27015
- Current status: enabled in AlphaGSM integration and smoke surfaces.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by app `740`.

## Developer Notes

### Run File

- **Executable**: `game/cs2.sh`
- **Location**: `<install_dir>/game/cs2.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `730`

### Server Configuration

- **Config files**: `game/csgo/cfg/server.cfg`
- **Template**: Source game config scaffold created during install

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: AlphaGSM can now track provider-id based CS2 server-side mod installs.

## Mod Sources

CS2 currently supports external provider-id mod sources rather than an
AlphaGSM-owned manifest.

- `gamebanana` means you provide a numeric GameBanana item id and AlphaGSM
	resolves the current downloadable archive from GameBanana.
- `moddb` means you provide a canonical Mod DB download or addon page URL and
	AlphaGSM resolves Mod DB's start-download link when the file is a supported
	zip or tar archive.
- `workshop` means you provide a Steam Workshop item ID or filedetails URL and AlphaGSM
	tries to download it through SteamCMD.
- `workshop-collection` expands a collection ID or filedetails URL into individual items.
  The collection and every nested item must belong to CS2 (AppID `730`).
  Imports preserve existing entries and skip duplicates. Both Workshop sources
  use anonymous login; access remains controlled by Steam. Only supported
  addon/config trees can be staged; arbitrary Workshop map packages are not
  installed by this adapter.
- AlphaGSM records the files installed for each CS2 mod entry so `mod cleanup`
	removes only tracked files and leaves unrelated files alone.

Examples:

```bash
alphagsm mycs2 mod add gamebanana 12345
alphagsm mycs2 mod add moddb https://www.moddb.com/mods/cage-eight/downloads/cage-eight
alphagsm mycs2 mod add workshop 1234567890
alphagsm mycs2 mod add workshop-collection COLLECTION_ID
alphagsm mycs2 mod apply
alphagsm mycs2 mod cleanup
```
