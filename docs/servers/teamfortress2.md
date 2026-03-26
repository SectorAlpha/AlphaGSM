# Team Fortress 2-specific

This guide covers the `teamfortress2` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myteamfort create teamfortress2
```

Run setup:

```bash
alphagsm myteamfort setup
```

Start it:

```bash
alphagsm myteamfort start
```

Check it:

```bash
alphagsm myteamfort status
```

Stop it:

```bash
alphagsm myteamfort stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myteamfort update
alphagsm myteamfort backup
```

## Notes

- Module name: `teamfortress2`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `232250`

### Server Configuration

- **Config files**: `server.cfg`
- **Template**: See [server-templates/teamfortress2/](../server-templates/teamfortress2/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
