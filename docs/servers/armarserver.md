# Arma Reforger

This guide covers the `armarserver` module in AlphaGSM.

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
