# Stormworks

This guide covers the `stormworksserver` module in AlphaGSM.

## Support Status

`stormworksserver` is supported in `ENABLED (BYO)` mode. The old standalone
Steam app `1247090` is now only a redirect stub, so AlphaGSM cannot fully
provision this lane anonymously anymore.

## Requirements

- `screen`
- an owned Stormworks dedicated server tree from the purchased game
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystormwor create stormworksserver
```

Run setup:

```bash
alphagsm mystormwor setup
```

Then stage the real owned server files into the install directory so
`server64.exe` and its runtime data come from the purchased game, not the
discontinued standalone stub.

Start it:

```bash
alphagsm mystormwor start
```

Check it:

```bash
alphagsm mystormwor status
```

Stop it:

```bash
alphagsm mystormwor stop
```

## Setup Details

Setup configures:

- the game port (default 25566)
- the install directory
- AlphaGSM records where the owned server tree should live

## Bring Your Own Steps

1. Run `alphagsm mystormwor create stormworksserver`.
2. Run `alphagsm mystormwor setup` so AlphaGSM records the install directory.
3. Copy an owned Stormworks dedicated server tree into that install directory.
4. Re-run `alphagsm mystormwor start`.

If `setup` or `start` reports an `ENABLED (BYO)` message, replace the staged
files with the real owned server tree and retry.

## Useful Commands

```bash
alphagsm mystormwor update
alphagsm mystormwor backup
```

## Notes

- Module name: `stormworksserver`
- Default port: 25566

## Developer Notes

### Run File

- **Executable**: `server64.exe`
- **Location**: `<install_dir>/server64.exe`
- **Engine**: Custom (owned install)
- **SteamCMD App ID**: `1247090`

### Server Configuration

- **Config file**: `server_config.xml`
- **Template**: See [server-templates/stormworksserver/](../server-templates/stormworksserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
