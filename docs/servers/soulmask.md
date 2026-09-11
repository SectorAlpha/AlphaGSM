# Soulmask

This guide covers the `soulmask` module in AlphaGSM.

`soulmask` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `wine-proton` runtime. `query` and `info`
use the validated generic TCP health surface on the managed game port under
Linux/Wine.

## Requirements

- `docker` for the validated Linux Wine/Proton path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysoulmask create soulmask
```

Run setup:

```bash
alphagsm mysoulmask setup
```

Start it:

```bash
alphagsm mysoulmask start
```

Check it:

```bash
alphagsm mysoulmask status
```

Stop it:

```bash
alphagsm mysoulmask stop
```

## Setup Details

Setup configures:

- the game port (default 8777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysoulmask update
alphagsm mysoulmask backup
```

## Notes

- Module name: `soulmask`
- Default port: `8777`
- Validated Linux runtime: Docker-backed `wine-proton`
- Query/info contract on Linux: generic TCP on the managed game port

<!-- alphagsm-server-variables:start -->

## Server variables

After `create soulmask`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `adminpassword` | adminpass | string | Administrator password. Stored as a secret. |
| `backupinterval` | — | integer | Backup interval in seconds. |
| `bindaddress` | — | string | Hosted IP address to bind for launch. |
| `dir` | — | string | Install directory for the server. |
| `echoport` | — | integer | Echo service port. |
| `exe_name` | — | string | Server executable filename. |
| `level` | — | string | The startup world or map. |
| `maxplayers` | users | integer | The maximum number of players. Example: `16`. |
| `mods` | — | string | Optional mod list. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |
| `queryport` | — | integer | The query port for the server. Example: `27015`. |
| `savinginterval` | — | integer | Autosave interval in seconds. |
| `servername` | hostname, name | string | The advertised server name. Example: `AlphaGSM Server`. |
| `serverpassword` | sv_password, password | string | Server password. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `WSServer.exe`
- **Location**: `<install_dir>/WSServer.exe`
- **Engine**: Windows dedicated server under Wine/Proton on Linux
- **SteamCMD App ID**: `3017310`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `10`
- **Template**: See [server-templates/soulmask/](../server-templates/soulmask/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
