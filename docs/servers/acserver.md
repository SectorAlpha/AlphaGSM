# Assetto Corsa

This guide covers the `acserver` module in AlphaGSM.

`acserver` is `ENABLED (AUTH)`: setup and updates require a Steam account
entitled to Assetto Corsa dedicated server app `302550`. Anonymous SteamCMD
returned `No subscription` in GitHub CI run `34289635472` on September 8, 2026.
This is the original Assetto Corsa; Competizione uses the separate `accserver` module.

The [maintained AMP installer](https://github.com/CubeCoders/AMPTemplates/blob/main/assetto-corsa.kvp)
requires Steam login. Its [download settings](https://github.com/CubeCoders/AMPTemplates/blob/main/assetto-corsaupdates.json)
select the Windows depot, which also supplies the native Linux `acServer` executable.
AlphaGSM uses that install path for both process and Docker runtimes.
Authenticated lifecycle validation remains pending.

## Requirements

- A Steam account with access to dedicated server app `302550`
- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myacserver create acserver
```

Configure the shared SteamCMD account in your private AlphaGSM configuration first:

```ini
[downloader.steamcmd]
username = your_steam_username
password = your_steam_password
```

Complete Steam Guard authentication for this account using SteamCMD as the same
operating-system user that runs AlphaGSM. The password setting can be omitted
when the SteamCMD session can log in without it. AlphaGSM checks that a
non-anonymous username is configured; Steam validates the actual entitlement.

Run setup:

```bash
alphagsm myacserver setup
```

Start it:

```bash
alphagsm myacserver start
```

Check it:

```bash
alphagsm myacserver status
```

Stop it:

```bash
alphagsm myacserver stop
```

## Setup Details

Setup configures:

- the game port (default 9600)
- the install directory
- Authenticated SteamCMD downloads the Windows depot containing `acServer`
- HTTP server port: 8081 by default

## Useful Commands

```bash
alphagsm myacserver update
alphagsm myacserver backup
```

## Notes

- Module name: `acserver`
- Default game port: 9600

<!-- alphagsm-server-variables:start -->

## Server variables

After `create acserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `acServer`
- **Location**: `<install_dir>/acServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `302550`

### Server Configuration

- **Config file**: `cfg/server_cfg.ini`
- **Default port**: `9600`
- **Template**: See [server-templates/acserver/](../server-templates/acserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
