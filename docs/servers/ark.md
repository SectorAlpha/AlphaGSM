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
- **Workshop support**: anonymous Linux gameplay-mod and custom-map staging;
  fresh process/Docker engine validation is pending.

## Workshop mods and maps

```bash
alphagsm myserver mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=2860800256
alphagsm myserver mod add workshop-collection COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver start
```

AlphaGSM validates items against ARK: Survival Evolved game AppID `346110`,
downloads anonymously, and validates native `mod.info` and `modmeta.info`.
Stackable gameplay mods (`ModType=1`) and custom maps (`ModType=2`) require
`WindowsNoEditor` cooked content, which the native Linux dedicated server also
uses. AlphaGSM follows [ARK Server Tools' Windows mod-branch default](https://github.com/arkmanager/ark-server-tools/blob/master/tools/arkmanager),
whose upstream warning identifies the Linux-cooked branch as a server crash
source. Linux-only payloads and total conversions are rejected.
Custom-map metadata must declare a safe map name that resolves to exactly one
staged native `.umap`; missing or ambiguous maps fail before publication.
Optional native metadata strings may use Unreal's zero-length empty-string
encoding. String bounds, terminators and map-name validation still apply.

Compressed `.z` assets are decompressed with checked chunk sizes and bounded
output. Native assets and a binary `.mod` descriptor are published under
`ShooterGame/Content/Mods/`. The ordered `ActiveMods` setting in
`ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini` preserves operator
IDs and unrelated settings. Per-file decompression is limited to 1 GiB and
each mod to 8 GiB of unpacked content. Custom maps use their exact staged
`/Game/Mods/ID/.../MapName` path and `MapModID`; they are not mixed into the
gameplay `GameModIds` launch list. Merely installing a map leaves `TheIsland`
selected until you explicitly change `map`.

For the small public [Very Flat Map](https://steamcommunity.com/sharedfiles/filedetails/?id=2041231763)
fixture (author's map name `FlatMap`, listed payload 3.372 MB):

```bash
alphagsm myserver mod add workshop 2041231763
alphagsm myserver mod apply
alphagsm myserver set map /Game/Mods/2041231763/FlatMap
alphagsm myserver start
alphagsm myserver info --json
```

CI run `38702811625` downloaded and staged the map, then both native runtime
tests crashed with `LinkerLoad: Bad name index` while using `LinuxNoEditor`.
Fresh CI must verify the corrected Windows-cooked branch can serve the custom
world in both runtimes.

`mod remove workshop ID_OR_URL` followed by `mod apply` removes selected owned
content and activation IDs. `mod cleanup` clears all desired Workshop items.
Operator files remain present; modified owned files block replacement or cleanup.
Removing a gameplay mod can affect world objects created by that mod. Switch
back to an installed map before starting after custom-map cleanup. Native file
staging and `ActiveMods` alone do not establish a successful engine load.

Baseline smoke and integration runs use the stock world. They require a named
world and positive player capacity; the initial empty A2S response is insufficient.
The separate, currently unverified Workshop case requires
`ALPHAGSM_RUN_ARK_WORKSHOP=1`. It selects the declared `FlatMap` world and requires
fresh native successful-startup records on its exact staged map URL, plus real
A2S metadata naming `FlatMap` with positive player capacity. A stock-world
fallback, download result or activation ID cannot satisfy the assertion.
The Linux 361.7 server authenticated native RCON but returned only a generic
receipt for engine `GetAll`, so the fixture now proves custom-world execution
instead of relying on unsupported object introspection. Native activation IDs
and map paths are snapshotted before start so inspecting or stopping the live
container does not reopen an engine-private INI.
