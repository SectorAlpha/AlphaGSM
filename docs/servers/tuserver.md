# Tower Unite

This guide covers the `tuserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytower create tuserver
```

Run setup:

```bash
alphagsm mytower setup
```

Start it:

```bash
alphagsm mytower start
```

Check it:

```bash
alphagsm mytower status
alphagsm mytower query
alphagsm mytower info
```

Stop it:

```bash
alphagsm mytower stop
```

## Setup Details

Setup configures:

- the game port (default `7777`)
- the query port (default `27015`)
- the install directory
- SteamCMD downloads the server files
- a per-instance Tower Unite config file at `<install_dir>/Tower/Binaries/Linux/<server_name>.ini`

## Useful Commands

```bash
alphagsm mytower update
alphagsm mytower backup
```

## Notes

- Module name: `tuserver`
- Game: Tower Unite
- Engine: Unreal 4 dedicated server
- SteamCMD App ID: `439660`
- Executable: `<install_dir>/Tower/Binaries/Linux/TowerServer-Linux-Shipping`
- Launch args include `-MultiHome=0.0.0.0`, `-Port`, `-QueryPort`, and `-TowerServerINI=<server_name>.ini`
- AlphaGSM probes `query` and `info` over A2S on the configured `queryport`

## Developer Notes

- Default config template, when present: `<install_dir>/Tower/Binaries/Linux/TowerServer.ini`
- Managed instance config: `<install_dir>/Tower/Binaries/Linux/<server_name>.ini`
- Log directory: `<install_dir>/Tower/Saved/Logs`