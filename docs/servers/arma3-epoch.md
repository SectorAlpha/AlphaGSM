# Namespaced Arma 3 Epoch

This guide covers the `arma3.epoch` module in AlphaGSM.

## Status

`arma3.epoch` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Arma 3 dedicated server app `233780`.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myepoch create arma3.epoch
```

Run setup:

```bash
alphagsm myepoch setup
```

Start it:

```bash
alphagsm myepoch start
```

Check it:

```bash
alphagsm myepoch status
```

Stop it:

```bash
alphagsm myepoch stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm myepoch update
alphagsm myepoch backup
```

## Notes

- Module name: `arma3.epoch`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create arma3.epoch`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `servername` | hostname, name | string | The public hostname written to server.cfg. Example: `AlphaGSM Server`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: See game module source
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/arma3-epoch/](../server-templates/arma3-epoch/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
