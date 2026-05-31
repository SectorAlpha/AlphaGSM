# The Isle

This guide covers the `tiserver` module in AlphaGSM.

## Support Status

`tiserver` is supported in `ENABLED (BYO)` mode.

AlphaGSM can:

- install the native Linux dedicated-server payload anonymously from SteamCMD app `412680`
- manage the server lifecycle through AlphaGSM
- run the server on the shared `steamcmd-linux` Docker runtime

The remaining operator-provided prerequisite is Epic Online Services dedicated-server authentication:

- `eos_client_id`
- `eos_client_secret`

Without those credentials the server exits during EOS platform startup with `Unable to initialize EOS platform.`

## Quick Start

Create the server:

```bash
alphagsm mytiserver create tiserver
```

Run setup:

```bash
alphagsm mytiserver setup
```

Set the required EOS credentials:

```bash
alphagsm mytiserver set eos_client_id YOUR_EOS_DEDICATED_SERVER_CLIENT_ID
alphagsm mytiserver set eos_client_secret YOUR_EOS_DEDICATED_SERVER_CLIENT_SECRET
```

Start it:

```bash
alphagsm mytiserver start
```

Check it:

```bash
alphagsm mytiserver status
```

Stop it:

```bash
alphagsm mytiserver stop
```

## Requirements

- Docker for the supported Linux runtime path
- SteamCMD
- Epic Online Services dedicated-server credentials for The Isle EVRIMA

## Setup Details

Setup configures:

- the game port
- the query port
- the install directory
- the native Linux dedicated-server payload from Steam app `412680`

## EOS Credentials

The Isle EVRIMA dedicated server now installs anonymously on Linux, but it will not finish booting until you provide valid EOS dedicated-server credentials.

AlphaGSM expects them as datastore keys:

- `eos_client_id`
- `eos_client_secret`

The official guide also supports file-based configuration in:

- `TheIsle/Saved/Config/LinuxServer/Engine.ini`

but AlphaGSM's supported operator flow is to store the values with `set` and let the module pass them on startup.

## Useful Commands

```bash
alphagsm mytiserver update
alphagsm mytiserver backup
alphagsm mytiserver dump
```

## Notes

- Module name: `tiserver`
- Steam App ID: `412680`
- Default game port: `7777`
- Default query port: `7778`
- Default executable: `TheIsleServer.sh`

## Developer Notes

### Run File

- **Executable**: `TheIsleServer.sh`
- **Binary**: `TheIsle/Binaries/Linux/TheIsleServer-Linux-Shipping`
- **Location**: `<install_dir>/TheIsleServer.sh`
- **Engine**: Unreal Engine native Linux dedicated server
- **SteamCMD App ID**: `412680`

### Runtime Notes

- The validated install layout is a real native Linux server payload, not a missing-binary app stub.
- The Linux container path must run as a non-root user; the dedicated binary refuses to run as root.
- EOS authentication is the remaining prerequisite for a full green integration path.
