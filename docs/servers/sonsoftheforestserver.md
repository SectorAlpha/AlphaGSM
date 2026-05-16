# Sons Of The Forest

This guide covers the `sonsoftheforestserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysonsofth create sonsoftheforestserver
```

Run setup:

```bash
alphagsm mysonsofth setup
```

Start it:

```bash
alphagsm mysonsofth start
```

Check it:

```bash
alphagsm mysonsofth status
```

Stop it:

```bash
alphagsm mysonsofth stop
```

## Setup Details

Setup configures:

- the game port (default 8766)
- the A2S query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mysonsofth update
alphagsm mysonsofth backup
```

## Notes

- Module name: `sonsoftheforestserver`
- Default game port: `8766`
- Default query port: `27015`

## Developer Notes

### Run File

- **Executable**: `SonsOfTheForestDS.exe`
- **Location**: `<install_dir>/SonsOfTheForestDS.exe`
- **Engine**: Unity Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2465200`

AlphaGSM launches the dedicated server executable directly instead of the
legacy `StartSOTFDedicated.bat` wrapper.

### Server Configuration

- **Config files**: `dedicatedserver.cfg`
- **Template**: See [server-templates/sonsoftheforestserver/](../server-templates/sonsoftheforestserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
