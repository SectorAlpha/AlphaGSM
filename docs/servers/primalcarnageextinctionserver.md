# Primal Carnage: Extinction

This guide covers the `primalcarnageextinctionserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprimalca create primalcarnageextinctionserver
```

Run setup:

```bash
alphagsm myprimalca setup
```

Start it:

```bash
alphagsm myprimalca start
```

Check it:

```bash
alphagsm myprimalca status
```

Stop it:

```bash
alphagsm myprimalca stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the A2S query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myprimalca update
alphagsm myprimalca backup
```

## Notes

- Module name: `primalcarnageextinctionserver`
- Default game port: `7777`
- Default query port: `27015`

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/PrimalCarnageServer.exe`
- **Location**: `<install_dir>/Binaries/Win64/PrimalCarnageServer.exe`
- **Engine**: UE3 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `336400`

Current validation status: the 2026-05-28 follow-up now checks in the best
known dedicated launcher (`SERVER PC-Docks?...?bIsDedicated=true
-seekfreeloadingserver -log`) and wraps it with `xvfb-run` on Linux. Focused
validation now also retries AlphaGSM's recommended claimed-port overrides so
an unmanaged listener on the default `queryport` `27015` no longer blocks
setup, but the remaining blocker is still after real dedicated startup: the
fresh rerun with `queryport=27016` again collapsed back to a dead screen
session and zero-byte `Launch.log` after Wine reported `Failed to read file
'PCDataStore_GameResource'` and an X `BadWindow` teardown. Keep this server in
the validation queue rather than marking it enabled yet.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/primalcarnageextinctionserver/](../server-templates/primalcarnageextinctionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
