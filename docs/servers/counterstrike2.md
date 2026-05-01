# counterstrike2

This guide covers the `counterstrike2` module in AlphaGSM.

```bash
alphagsm myserver create counterstrike2
```

`cs2server` is an alias for this module.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycs2 create counterstrike2
```

Run setup:

```bash
alphagsm mycs2 setup
```

Start it:

```bash
alphagsm mycs2 start
```

Check it:

```bash
alphagsm mycs2 status
```

Stop it:

```bash
alphagsm mycs2 stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files for Steam app `730`
- the launcher defaults to `game/cs2.sh`
- Source config is written under `game/csgo/cfg/server.cfg`

## Notes

- Module name: `counterstrike2`
- Default port: 27015
- Current status: enabled in AlphaGSM integration and smoke surfaces.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by app `740`.

## Developer Notes

### Run File

- **Executable**: `game/cs2.sh`
- **Location**: `<install_dir>/game/cs2.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `730`

### Server Configuration

- **Config files**: `game/csgo/cfg/server.cfg`
- **Template**: Source game config scaffold created during install

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: AlphaGSM can now track provider-id based CS2 server-side mod installs.

## Mod Sources

CS2 currently supports external provider-id mod sources rather than an
AlphaGSM-owned manifest.

- `gamebanana` means you provide a numeric GameBanana item id and AlphaGSM
	resolves the current downloadable archive from GameBanana.
- `moddb` means you provide a canonical Mod DB download or addon page URL and
	AlphaGSM resolves Mod DB's start-download link when the file is a supported
	zip or tar archive.
- `workshop` means you provide a numeric Steam Workshop item id and AlphaGSM
	tries to download it through SteamCMD.
- AlphaGSM records the files installed for each CS2 mod entry so `mod cleanup`
	removes only tracked files and leaves unrelated files alone.

Examples:

```bash
alphagsm mycs2 mod add gamebanana 12345
alphagsm mycs2 mod add moddb https://www.moddb.com/mods/cage-eight/downloads/cage-eight
alphagsm mycs2 mod add workshop 1234567890
alphagsm mycs2 mod apply
alphagsm mycs2 mod cleanup
```
