# Beasts of Bermuda

This guide covers the `bobserver` module in AlphaGSM.

`bobserver` is currently `DISABLED` in the checked-in support tracker. Prior
CI runs timed out during the large SteamCMD app `882430` download; the
integration test now allows 30 minutes and leaves that failure visible rather
than permanently skipping it. AlphaGSM keeps the module hard-disabled until a
fresh GitHub CI run validates the install and lifecycle on Ubuntu 24.04.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybobserve create bobserver
```

Run setup:

```bash
alphagsm mybobserve setup
```

Start it:

```bash
alphagsm mybobserve start
```

Check it:

```bash
alphagsm mybobserve status
```

Stop it:

```bash
alphagsm mybobserve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the `Test_Performance` map by default
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybobserve update
alphagsm mybobserve backup
```

## Notes

- Module name: `bobserver`
- Default game port: 7777
- Default query port: 27015

## Developer Notes

### Run File

- **Executable**: `BeastsOfBermudaServer.sh`
- **Location**: `<install_dir>/LinuxServer/BeastsOfBermudaServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `882430`

The launcher receives the documented `-Port=`, `-QueryPort=`, `-SessionName`,
`-MapName`, and optional `-ServerPassword` arguments.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/bobserver/](../server-templates/bobserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
