# BATTALION: Legacy

This guide covers the `btlserver` module in AlphaGSM.

`btlserver` is currently `PASSED` in the checked-in support tracker on the
documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane
validates both process and Docker runtimes for this module, while local runs
remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybtlserve create btlserver
```

Run setup:

```bash
alphagsm mybtlserve setup
```

Start it:

```bash
alphagsm mybtlserve start
```

Check it:

```bash
alphagsm mybtlserve status
```

Stop it:

```bash
alphagsm mybtlserve stop
```

## Setup Details

Setup configures:

- the game port (default 7788)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybtlserve update
alphagsm mybtlserve backup
```

## Notes

- Module name: `btlserver`
- Default port: 7788
- The Docker contract launches the Unreal payload as the mapped host user;
  the game refuses to run as root.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create btlserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `map` | gamemap, startmap, level, worldname | string | The startup map. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |
| `queryport` | — | integer | The query port for the server. Example: `27015`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `Battalion/Binaries/Linux/BattalionServer-Linux-Shipping`
- **Location**: `<install_dir>/Battalion/Binaries/Linux/BattalionServer-Linux-Shipping`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `805140`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/btlserver/](../server-templates/btlserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
