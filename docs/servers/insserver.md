# Insurgency

This guide covers the `insserver` module in AlphaGSM.

`insserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myinsserve create insserver
```

Run setup:

```bash
alphagsm myinsserve setup
```

Start it:

```bash
alphagsm myinsserve start
```

Check it:

```bash
alphagsm myinsserve status
```

Stop it:

```bash
alphagsm myinsserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm myinsserve update
alphagsm myinsserve backup
```

## Notes

- Module name: `insserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create insserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `embassy_coop checkpoint`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `32`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Insurgency`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `237410`

Smoke and integration validation treat startup as complete once the server log
reaches the normal Source markers and `alphagsm info --json` reports `a2s`.

### Server Configuration

- **Config file**: `insurgency/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `embassy_coop checkpoint`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/insserver/](../server-templates/insserver/)

### Maps and Mods

- **Map directory**: `insurgency/maps/`
- **Mod directory**: `insurgency/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM can now manage Insurgency addons from checked-in `manifest` entries plus direct archive `url` entries, GameBanana ids, and Mod DB page URLs. The local manifest currently includes popular Source admin/plugin stacks such as MetaMod and SourceMod. Archives must unpack into approved addon paths under `insurgency/addons/`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/insurgency/`.
- **Map install**: Copy `.bsp` files into `insurgency/maps/` and add to `insurgency/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `insurgency/addons/`.

Examples:

```bash
alphagsm myins mod add manifest metamod
alphagsm myins mod add manifest sourcemod
alphagsm myins mod add url https://mods.example.invalid/ins-addon-pack.zip
alphagsm myins mod add gamebanana 12345
alphagsm myins mod add moddb https://www.moddb.com/mods/example/downloads/example-addon-pack
alphagsm myins mod apply
alphagsm myins mod cleanup
```
