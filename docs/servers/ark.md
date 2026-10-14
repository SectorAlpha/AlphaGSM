# ARK: Survival Evolved

This guide covers the `ark` module in AlphaGSM.

`ark` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline.
The checked-in GitHub validation path for this server is Docker-first through
the shared `steamcmd-linux` runtime, with the real Linux dedicated server
answering A2S `query`, `info`, and `info --json` on the managed `queryport`.
The CI permission fix passed Docker smoke and integration on 2026-10-14: Docker uses the
manager's user/group IDs, a private writable home and read-only Steam SDK
mounts. It does not recursively widen game-file permissions.

## Requirements

- Docker or another supported AlphaGSM runtime backend
- SteamCMD access for app `376030`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myark create ark
```

Run setup:

```bash
alphagsm myark setup
```

Start it:

```bash
alphagsm myark start
```

Check it:

```bash
alphagsm myark status
```

Stop it:

```bash
alphagsm myark stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myark update
alphagsm myark backup
```

## Notes

- Module name: `ark`
- Default game port: `7777`
- Default query port: `27015`
- Validated Linux support path: Docker `steamcmd-linux` runtime with A2S `query` / `info` on `queryport`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ark`, inspect or change these with `set`:

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

- **Executable**: `ShooterGame/Binaries/Linux/ShooterGameServer`
- **Location**: `<install_dir>/ShooterGame/Binaries/Linux/ShooterGameServer`
- **Engine**: Native Linux dedicated server via SteamCMD
- **SteamCMD App ID**: `376030`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/ark/](../server-templates/ark/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: anonymous stackable Linux gameplay-mod staging;
  fresh process/Docker engine validation is pending.

## Workshop gameplay mods

```bash
alphagsm myserver mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=2860800256
alphagsm myserver mod add workshop-collection COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver start
```

AlphaGSM validates items against ARK: Survival Evolved game AppID `346110`,
downloads anonymously, and validates native `mod.info` and `modmeta.info`.
Stackable gameplay mods (`ModType=1`) with `LinuxNoEditor` content are supported;
map mods, total conversions and Windows-only payloads are rejected.

Compressed `.z` assets are decompressed with checked chunk sizes and bounded
output. Native assets and a binary `.mod` descriptor are published under
`ShooterGame/Content/Mods/`. The ordered `ActiveMods` setting in
`ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini` preserves operator
IDs and unrelated settings. Per-file decompression is limited to 1 GiB and
each mod to 8 GiB of unpacked content.

`mod remove workshop ID_OR_URL` followed by `mod apply` removes selected owned
content and activation IDs. `mod cleanup` clears all desired Workshop items.
Operator files remain present; modified owned files block replacement or cleanup.
Removing a gameplay mod can affect world objects created by that mod. The
[Meat Spoiler fixture](https://steamcommunity.com/sharedfiles/filedetails/?id=2860800256)
is intended for a disposable validation world. Native file staging and
`ActiveMods` alone do not establish a successful engine load.

Baseline smoke and integration runs use the stock world. They require a named
world and positive player capacity; the initial empty A2S response is insufficient.
The separate, currently unverified Workshop case requires
`ALPHAGSM_RUN_ARK_WORKSHOP=1`. Opting in retains the native Blueprint-load
assertion and surfaces its failure normally. Native activation IDs are snapshotted
before start so inspecting or stopping the live container does not reopen an
engine-private INI.

The Workshop case creates a disposable local RCON password in AlphaGSM's secret
store and allocates its own RCON port. It authenticates against the configured
runtime host, including the published-port gateway for sibling Docker containers,
then runs `getall PrimalGameData_BP_Spoilers_C ModName SHOWDEFAULTS`. A numbered
native object record must name that Blueprint and its nonempty Meat Spoiler
`ModName` property. Command receipts and launch/config IDs do not count as proof.
The class default object is included because ARK loads stackable Blueprint game
data before merging it into the world. The server flushes native logging to files
and stdout; the probe also accepts the authenticated RCON property response.
This replaces stdin command delivery, which can succeed without ARK executing the
command, and the old property-less `getall` probe. Fresh CI must still confirm
that the shipped native server exposes this property through RCON.
