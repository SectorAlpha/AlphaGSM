# Unturned

This guide covers the `unturned` module in AlphaGSM.

`unturned` is currently `PASSED` in the checked-in support tracker on the
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
alphagsm myunturned create unturned
```

Run setup:

```bash
alphagsm myunturned setup
```

Start it:

```bash
alphagsm myunturned start
```

Check it:

```bash
alphagsm myunturned status
```

Stop it:

```bash
alphagsm myunturned stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

AlphaGSM writes native settings to `Servers/<serverid>/Server/Commands.dat`.
The configured base port is used for Steam A2S queries; gameplay uses the next
UDP port. Open both ports when configuring your firewall.

## Useful Commands

```bash
alphagsm myunturned update
alphagsm myunturned backup
```

## Notes

- Module name: `unturned`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create unturned`, inspect or change these with `set`:

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

- **Executable**: `ServerHelper.sh`
- **Location**: `<install_dir>/ServerHelper.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1110390`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/unturned/](../server-templates/unturned/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
