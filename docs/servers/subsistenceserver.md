# Subsistence

This guide covers the `subsistenceserver` module in AlphaGSM.

`subsistenceserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `wine-proton` runtime, with A2S `query` /
`info` on the managed `queryport`.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysubsiste create subsistenceserver
```

Run setup:

```bash
alphagsm mysubsiste setup
```

Start it:

```bash
alphagsm mysubsiste start
```

Check it:

```bash
alphagsm mysubsiste status
```

Stop it:

```bash
alphagsm mysubsiste stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the A2S query port (default 27016)
- the max players value (default 10)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mysubsiste update
alphagsm mysubsiste backup
```

## Notes

- Module name: `subsistenceserver`
- Default game port: `27015`
- Default query port: `27016`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create subsistenceserver`, inspect or change these with `set`:

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

- **Executable**: `Binaries/Win64/UDK.exe`
- **Location**: `<install_dir>/Binaries/Win64/UDK.exe`
- **Engine**: UE3 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `1362640`

Current validation status: passed on the shared Docker `wine-proton` runtime.
The current supported Linux lane uses the upstream `Binaries/Win64/UDK.exe`
launcher with AlphaGSM-managed UDK config sync. The dedicated server answers
`query`, `info`, and `info --json` over A2S on the managed `queryport`.

### Server Configuration

- **Config files**:
  - `<install_dir>/UDKGame/Config/UDKEngine.ini`
  - `<install_dir>/UDKGame/Config/DefaultEngine.ini`
  - `<install_dir>/UDKGame/Config/DefaultEngineUDK.ini`
  - `<install_dir>/UDKGame/Config/UDKDedServerSettings.ini`
  - `<install_dir>/UDKGame/Config/DefaultDedServerSettings.ini`
- **Max players**: `10`
- **Template**: See [server-templates/subsistenceserver/](../server-templates/subsistenceserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
