# Arma Reforger

This guide covers the `armarserver` module in AlphaGSM.

`armarserver` is currently listed as `PASSED` in the checked-in support tracker on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection around this SteamCMD-backed lifecycle, but the checked-in integration test still carries an upstream install skip note and should be revalidated before treating that tracker row as freshly proven.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarmarser create armarserver
```

Run setup:

```bash
alphagsm myarmarser setup
```

Start it:

```bash
alphagsm myarmarser start
```

Check it:

```bash
alphagsm myarmarser status
```

Stop it:

```bash
alphagsm myarmarser stop
```

## Setup Details

Setup configures:

- the game port (default 2001)
- the install directory
- SteamCMD downloads the server files

## Structured Settings

AlphaGSM exposes the JSON-backed settings through `set`:

```bash
alphagsm myarmarser set map "{ECC61978EDCC2B5A}Missions/23_Campaign.conf"
alphagsm myarmarser set adminpassword "super-secret"
alphagsm myarmarser set bindaddress 0.0.0.0
```

The `map` setting writes the `scenarioid` field in `configs/server.json`.

## Useful Commands

```bash
alphagsm myarmarser update
alphagsm myarmarser backup
```

## Notes

- Module name: `armarserver`
- Default port: 2001

<!-- alphagsm-server-variables:start -->

## Server variables

After `create armarserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `adminpassword` | adminpass | string | Password used for administrative access. Stored as a secret. |
| `bindaddress` | — | string | IP address the server binds its A2S listener to. Example: `0.0.0.0`. |
| `map` | scenario, scenarioid, gamemap, startmap, level, worldname | string | The selected scenario file used by the server. Example: `{ECC61978EDCC2B5A}Missions/23_Campaign.conf`. |
| `maxplayers` | users | integer | Maximum number of players allowed on the server. Example: `8`. |
| `port` | gameport | integer | The primary game port. Example: `2001`. |
| `queryport` | — | integer | The A2S query port. Example: `2002`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `ArmaReforgerServer`
- **Location**: `<install_dir>/ArmaReforgerServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1874900`

### Server Configuration

- **Config file**: `configs/server.json`
- **Template**: See [server-templates/armarserver/](../server-templates/armarserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
