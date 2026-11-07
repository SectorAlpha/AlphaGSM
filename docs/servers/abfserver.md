# Abiotic Factor

This guide covers the `abfserver` module in AlphaGSM.

`abfserver` is currently `DISABLED` in the checked-in support tracker. The
dedicated-server tool is Windows-only, so AlphaGSM now stages its Windows
payload with SteamCMD's forced-platform option and uses the shared Wine/Proton
runtime on Linux. The end-to-end Docker lifecycle still needs fresh GitHub CI
validation before this module can be enabled.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myabfserve create abfserver
```

Run setup:

```bash
alphagsm myabfserve setup
```

Start it:

```bash
alphagsm myabfserve start
```

Check it:

```bash
alphagsm myabfserve status
```

Stop it:

```bash
alphagsm myabfserve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myabfserve update
alphagsm myabfserve backup
```

## Notes

- Module name: `abfserver`
- Default game port: 7777
- Default query port: 27016

<!-- alphagsm-server-variables:start -->

## Server variables

After `create abfserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |
| `queryport` | — | integer | The query port for the server. Example: `27015`. |
| `world` | — | string | The saved world name to load. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `AbioticFactorServer-Win64-Shipping.exe`
- **Location**: `<install_dir>/AbioticFactor/Binaries/Win64/AbioticFactorServer-Win64-Shipping.exe`
- **Engine**: Unreal Engine (SteamCMD, Wine/Proton on Linux)
- **SteamCMD App ID**: `2857200`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/abfserver/](../server-templates/abfserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
