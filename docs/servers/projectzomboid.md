# Project Zomboid

This guide covers the `projectzomboid` module in AlphaGSM.

`projectzomboid` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprojectz create projectzomboid
```

Run setup:

```bash
alphagsm myprojectz setup
```

Start it:

```bash
alphagsm myprojectz start
```

Check it:

```bash
alphagsm myprojectz status
```

Stop it:

```bash
alphagsm myprojectz stop
```

## Setup Details

Setup configures:

- the game port (default 16261)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myprojectz update
alphagsm myprojectz backup
```

## Notes

- Module name: `projectzomboid`
- Default port: 16261

<!-- alphagsm-server-variables:start -->

## Server variables

After `create projectzomboid`, inspect or change these with `set`:

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

- **Executable**: `start-server.sh`
- **Location**: `<install_dir>/start-server.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `380870`

### Server Configuration

- **Config file**: `<install_dir>/Zomboid/Server/<servername>.ini`
- **Template**: See [server-templates/projectzomboid/](../server-templates/projectzomboid/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: Native Workshop activation through `mod` (Build 41/42 metadata; maps require manual ordering)

## Native Steam Workshop mods

Stop the server before changing mods, then record and apply a Workshop item or
collection:

```bash
alphagsm myprojectz stop
alphagsm myprojectz mod add workshop 2773478544
# Or: alphagsm myprojectz mod add workshop-collection COLLECTION_ID_OR_URL
alphagsm myprojectz mod apply
alphagsm myprojectz mod list
alphagsm myprojectz start
alphagsm myprojectz logs -n 200
```

`mod add` records desired state. `mod apply` validates every item against the
Project Zomboid game Workshop (AppID `108600`), downloads it anonymously for
inspection, and reads its actual `mod.info` IDs. The server-tool AppID `380870`
is used only for installing the dedicated server. AlphaGSM writes numeric
Workshop IDs into `WorkshopItems=` and the distinct internal Mod IDs into
`Mods=`. The game downloads its native Workshop cache when it starts.
When `mods.autoapply` is disabled, setup, update and startup preserve existing
native activation. An explicit `mod apply` still reconciles the desired list.

AlphaGSM detects the installed Build 41 or Build 42 engine, selects the matching
mod metadata, checks declared version ranges and required dependencies, and
orders dependencies before their dependants. Build 42 activation uses the
native backslash prefix. Add every prerequisite Workshop item explicitly;
missing prerequisites, duplicate IDs, conflicting mods and cyclic load order
fail before changing activation. A package containing a mod with no compatible
build is rejected. Map packages are rejected because `Map=` ordering and world
compatibility require a separate manual workflow.

Workshop startup has been verified on Build 42.21 through both process and
Docker runtimes. Build 41 metadata handling has unit coverage; its native
Workshop startup has not been revalidated in this change.

Configuration, saves and native logs live in `<install_dir>/Zomboid/`, selected
by `-cachedir=./Zomboid` for both process and Docker runtimes. The profile is
`Zomboid/Server/<servername>.ini`. `set port` and `set queryport` synchronize
`DefaultPort` and `UDPPort`, preserving other settings. Before upgrading an
existing home-directory installation, stop it and move its matching profile,
associated server files, database and save data from `~/Zomboid/` into this
install-local cache. AlphaGSM refuses a conflicting home profile instead of
silently launching a different world.

Unrelated settings and operator-supplied `WorkshopItems`/`Mods` entries are
preserved. Remove an AlphaGSM-managed item and reconcile the remaining list:

```bash
alphagsm myprojectz stop
alphagsm myprojectz mod remove workshop 2773478544
alphagsm myprojectz mod apply
alphagsm myprojectz start
```

`mod cleanup` removes only AlphaGSM-owned activation entries and clears the
managed Workshop desired list. The game and SteamCMD caches are retained. `mod list` reports configured state;
a configured file or downloaded payload does not establish that the engine
loaded the mod. Check fresh native Workshop Ready/install messages and the
mod's server-side execution output after restarting.

The opt-in integration test uses the small multiplayer
[Print Ingame Time One Hour & Death to LOG](https://steamcommunity.com/sharedfiles/filedetails/?id=2773478544)
fixture. It requires both native Workshop Ready/install evidence and execution
of the fixture's server Lua (`Date in game (dd/mm/yyyy)`) on a fresh launch,
then runs status/query/info and verifies shutdown. Run its process and Docker
cases with `ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1
ALPHAGSM_RUN_WORKSHOP=1`; Docker uses the normal runtime-image configuration.
The smoke runner enables the same fixture with `ALPHAGSM_RUN_WORKSHOP=1`.

The native configuration split and install-local cache follow
[The Indie Stone's Workshop guidance](https://theindiestone.com/forums/topic/45463-added-mods-not-working/)
and [dedicated-server cache-directory guidance](https://theindiestone.com/forums/topic/42017-how-to-change-where-the-server-data-is-stored/).

For repeated validation, `ALPHAGSM_PROJECTZOMBOID_TEST_CACHE=/path/to/test-install`
copies an existing test depot into each fresh install, excluding worlds, native
Workshop caches and manager state. Setup still runs through AlphaGSM and
SteamCMD, and each case uses its own copied files and fresh profile.
