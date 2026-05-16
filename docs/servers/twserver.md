# Teeworlds

This guide covers the `twserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytwserver create twserver
```

Run setup:

```bash
alphagsm mytwserver setup
```

Start it:

```bash
alphagsm mytwserver start
```

Check it:

```bash
alphagsm mytwserver status
```

Stop it:

```bash
alphagsm mytwserver stop
```

## Setup Details

Setup configures:

- the game port (default 8303)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mytwserver update
alphagsm mytwserver backup
alphagsm mytwserver set port 8304
alphagsm mytwserver set servername "AlphaGSM Teeworlds Server"
```

`set port` and `set servername` rewrite `autoexec.cfg` immediately. The shared alias layer also accepts `hostname` and maps it to the Teeworlds `servername` setting.

## Notes

- Module name: `twserver`
- Default port: 8303

## Developer Notes

### Run File

- **Executable**: `teeworlds_srv`
- **Location**: `<install_dir>/teeworlds_srv`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `380840`

### Server Configuration

- **Config file**: `autoexec.cfg`
- **Template**: See [server-templates/twserver/](../server-templates/twserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `sv_port` and `sv_name` in sync with `set port` / `set servername`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
