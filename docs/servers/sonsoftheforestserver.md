# Sons Of The Forest

This guide covers the `sonsoftheforestserver` module in AlphaGSM.

`sonsoftheforestserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `wine-proton` runtime, with A2S `query` /
`info` on the managed `queryport`.

## Requirements

- Docker recommended on Linux (`alphagsm-wine-proton-runtime`)
- For host/process mode: `screen`, Wine or Proton-GE, and `xvfb-run`
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
- the A2S query port (default 27016)
- the blob sync port (default 9700)
- the install directory
- SteamCMD downloads the Windows dedicated server files
- AlphaGSM writes `user-data/dedicatedserver.cfg`, `steam_appid.txt`, and
  `user-data/ownerswhitelist.txt` before the first launch so the dedicated
  server clears its first-run self-tests without needing a manual restart

## Useful Commands

```bash
alphagsm mysonsofth update
alphagsm mysonsofth backup
```

## Notes

- Module name: `sonsoftheforestserver`
- Default game port: `8766`
- Default query port: `27016`
- Default blob sync port: `9700`
- Current AlphaGSM status: supported and validated on the Docker-backed
  `wine-proton` runtime, with A2S `query`, `info`, and `info --json` on the
  managed query port

## Developer Notes

### Run File

- **Executable**: `SonsOfTheForestDS.exe`
- **Location**: `<install_dir>/SonsOfTheForestDS.exe`
- **Engine**: Unity Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2465200`

AlphaGSM launches the dedicated server executable directly instead of the
legacy `StartSOTFDedicated.bat` wrapper, passing `-userdatapath ./user-data`
plus Unity's dedicated `-batchmode -nographics -verboseLogging` flags.

### Server Configuration

- **Config files**: `user-data/dedicatedserver.cfg`, `user-data/ownerswhitelist.txt`
- **Log file**: `user-data/logs/sotf_log.txt`
- **Template**: See [server-templates/sonsoftheforestserver/](../server-templates/sonsoftheforestserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
