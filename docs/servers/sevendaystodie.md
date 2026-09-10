# 7 Days to Die

This guide covers the `sevendaystodie` module in AlphaGSM.

Status: PASSED on 2026-05-29 on the native Linux SteamCMD path.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysevenday create sevendaystodie
```

Run setup:

```bash
alphagsm mysevenday setup
```

Start it:

```bash
alphagsm mysevenday start
```

Check it:

```bash
alphagsm mysevenday status
```

Stop it:

```bash
alphagsm mysevenday stop
```

## Setup Details

Setup configures:

- the game port (default 26900)
- the complete server network range: base TCP+UDP and UDP on `port + 1`,
  `port + 2`, and `port + 3`
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysevenday update
alphagsm mysevenday backup
alphagsm mysevenday set servername "AlphaGSM 7DTD"
alphagsm mysevenday set maxplayers 12
```

`set port`, `set servername`, `set maxplayers`, and `set serverpassword` rewrite `serverconfig.xml` immediately through the schema-backed config-sync path.

## Mod Sources

7 Days to Die mod management currently targets the built-in `Mods/` directory
under the server root.

- Current mod source support is direct archive `url` entries only.
- `mod add url <https-url>` accepts supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload exposes either `Mods/<name>/...`, a single top-level modlet directory containing `ModInfo.xml`, or multiple sibling modlet directories that each contain `ModInfo.xml`.
- `mod cleanup` removes only AlphaGSM-tracked modlet files and keeps its cache/state under `.alphagsm/mods/sevendaystodie/`.
- This first 7DTD slice intentionally focuses on built-in modlets and does not try to bootstrap an external framework.

Examples:

```bash
alphagsm mysevenday mod add url https://example.invalid/servertools.zip
alphagsm mysevenday mod apply
alphagsm mysevenday mod cleanup
```

## Notes

- Module name: `sevendaystodie`
- Default port: 26900
- AlphaGSM readiness for 7DTD follows the game's real `output_log__*.txt` file in the install root rather than the screen log.
- `query`, `info`, and `info --json` now validate against 7DTD's live A2S listener on the managed main port.
- AlphaGSM claims the full derived port set before either process or Docker
  launch and publishes the same set in Docker.
- On very long SteamCMD setups, refreshing the claimed port just before `start` avoids a stale free-port selection from the earlier setup step.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create sevendaystodie`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `maxplayers` | users | integer | Maximum allowed players. |
| `port` | gameport | integer | The game port to use for this server. |
| `servername` | hostname, name | string | The advertised server name. |
| `serverpassword` | sv_password, password | string | Optional join password. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `startserver.sh`
- **Location**: `<install_dir>/startserver.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `294420`

### Server Configuration

- **Config file**: `serverconfig.xml`
- **Template**: See [server-templates/sevendaystodie/](../server-templates/sevendaystodie/) if available
- **Schema-backed sync**: AlphaGSM keeps `ServerPort`, `ServerName`, `ServerMaxPlayerCount`, and `ServerPassword` aligned with `set`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: `Mods/`
- **Mod notes**: AlphaGSM can now track direct archive `url` entries for 7 Days to Die modlets, install recognized modlet payloads into `Mods/`, and clean up only AlphaGSM-managed files from `.alphagsm/mods/sevendaystodie/`.
- **Workshop support**: No
