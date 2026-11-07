# Conan Exiles

This guide covers the `conanexiles` module in AlphaGSM.

Status: enabled on native Linux; replacement CI validation is pending.

## Requirements

- Docker if you want the shared `steamcmd-linux` runtime path
- SteamCMD access for app `443030` (anonymous download works)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myconan create conanexiles
```

Run setup:

```bash
alphagsm myconan setup
```

Start it:

```bash
alphagsm myconan start
```

Check it:

```bash
alphagsm myconan status
alphagsm myconan query
alphagsm myconan info
```

Stop it:

```bash
alphagsm myconan stop
```

## Setup Details

Setup configures:

- the main game port, default `7777/udp`
- the dedicated query port, default `27015/udp`
- the install directory
- the official native Linux dedicated-server payload
- Conan's hardcoded pinger port at the game port plus one

## Config Files

AlphaGSM manages the normal Conan Exiles server config layout under:

- `<install_dir>/ConanSandbox/Saved/Config/LinuxServer/Engine.ini`
- `<install_dir>/ConanSandbox/Saved/Config/LinuxServer/Game.ini`
- `<install_dir>/ConanSandbox/Saved/Config/LinuxServer/ServerSettings.ini`

Checked-in starter templates live under [docs/server-templates/conanexiles/](../server-templates/conanexiles/).

AlphaGSM keeps these values aligned automatically:

- `port` -> `Engine.ini` `[URL] Port`
- `queryport` -> `Engine.ini` `[OnlineSubsystemNull] GameServerQueryPort`
- `servername` -> `Engine.ini` `[OnlineSubsystem] ServerName`
- `maxplayers` -> `Game.ini` `[/Script/Engine.GameSession] MaxPlayers`

When upgrading an existing Wine-based installation, AlphaGSM copies missing
settings from the old `WindowsServer` directory and renames the legacy
`Saved/Game.db` database to the lowercase filename expected by Linux. Existing
native files always win.

## Runtime Contract

- Preferred executable: `ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping`
- Container family: `steamcmd-linux`
- Docker runs the native server as the invoking host user because the binary
  refuses root privileges
- Query surface: A2S on the managed `queryport`
- Default map: `ConanSandbox`

The game port also exposes gameplay traffic on `port`, and Conan keeps a hardcoded pinger on `port + 1`.

## Useful Commands

```bash
alphagsm myconan set queryport 27015
alphagsm myconan set servername "AlphaGSM Conan"
alphagsm myconan set maxplayers 16
alphagsm myconan update
alphagsm myconan backup
```

<!-- alphagsm-server-variables:start -->

## Server variables

After `create conanexiles`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `map` | gamemap, startmap, level, worldname | string | The map to load when the Conan Exiles server starts. |
| `maxplayers` | users | integer | The maximum number of players. |
| `port` | gameport | integer | The main Conan Exiles game port. |
| `queryport` | — | integer | The Conan Exiles dedicated query port. |
| `servername` | hostname, name | string | The advertised Conan Exiles server name. |

<!-- alphagsm-server-variables:end -->

## Workshop mods

Ordered native PAK staging uses anonymous SteamCMD. Process and branch-local
Docker validation passed on 2026-10-13 with the Storage Reach Expanded fixture:
native PAK mounting, Blueprint mod execution, real A2S health, owned cleanup and
a fresh restart proving deactivation. Both stop paths used the existing timeout
and kill fallback; graceful saving remains unverified.

```bash
alphagsm myserver mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=3733835102
alphagsm myserver mod add workshop-collection COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver start
```

AlphaGSM validates items against game AppID `440900`, downloads anonymously,
and publishes PAKs under `ConanSandbox/Mods/<item-id>/`. Desired items retain
their load order in `ConanSandbox/Mods/modlist.txt`. Existing operator entries
remain present. `mod remove workshop ID_OR_URL` followed by `mod apply` removes
the selected owned files; `mod cleanup` clears all desired Workshop items.
Externally edited owned files block replacement or cleanup.
Conan may extract native cache files from the published PAK. AlphaGSM leaves
those game-generated caches in place; removing the modlist entry deactivates
the mod at the next start.

The [Storage Reach Expanded fixture](https://steamcommunity.com/sharedfiles/filedetails/?id=3733835102)
targets Conan Exiles Enhanced. Legacy and Enhanced mods are different payloads;
choose mods matching your installed server. The [official launcher documentation](https://forums.funcom.com/t/conan-exiles-dedicated-server-launcher-official-version-1-9-2-beta-1-9-3/21699)
describes ordered PAK lists and native `LogModManager` mounting evidence.
Downloads and a written modlist alone do not establish a successful engine load.
