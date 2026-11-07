# Soldat

This guide covers the `solserver` module in AlphaGSM.

`solserver` is currently `PASSED` in the checked-in support tracker on the
documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane
validates both process and Docker runtimes for this module, while local runs
remain process-backed by default unless you opt into the Docker backend.
The current launch and native query corrections await replacement CI validation.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysolserve create solserver
```

Run setup:

```bash
alphagsm mysolserve setup
```

Start it:

```bash
alphagsm mysolserve start
```

Check it:

```bash
alphagsm mysolserve status
```

Stop it:

```bash
alphagsm mysolserve stop
```

## Setup Details

Setup configures:

- the game port (default 23073)
- the install directory
- SteamCMD downloads the server files
- `soldat.ini` receives the managed port, player limit, and server name.
  Logging and downloads are enabled for the native public `gamestat.txt` query.

## Useful Commands

```bash
alphagsm mysolserve update
alphagsm mysolserve backup
```

## Notes

- Module name: `solserver`
- Default port: 23073
- `query` and `info` use the classic Soldat status service on TCP game port + 10
  (default 23083). Docker publishes it alongside the game port and runs as the
  invoking user, because Soldat exits when launched as root.
- Native status queries require a complete, valid response; a TCP connection
  alone does not establish readiness. See the [query client requirements](https://github.com/gamedig/node-gamedig/blob/master/GAMES_LIST.md#soldat).

<!-- alphagsm-server-variables:start -->

## Server variables

After `create solserver`, inspect or change these with `set`:

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

- **Executable**: `soldatserver`
- **Location**: `<install_dir>/soldatserver`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `638500`

### Server Configuration

- **Config file**: `soldat.ini` (existing `Soldat.ini`/`SOLDAT.INI` is also recognized)
- **Max players**: `16`
- **Template**: See [server-templates/solserver/](../server-templates/solserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
