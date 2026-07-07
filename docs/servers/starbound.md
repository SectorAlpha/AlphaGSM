# Starbound

This guide covers the `starbound` module in AlphaGSM.

`starbound` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that staged-native-server-tree prerequisite,
while local runs remain process-backed by default unless you opt into the
Docker backend.

## Requirements

- `screen`
- a native Starbound server tree containing `linux64/starbound_server`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystarboun create starbound
```

Run setup:

```bash
alphagsm mystarboun setup
```

`starbound` is supported in `ENABLED (BYO)` mode. The current anonymous
SteamCMD app does not ship the required Linux server binary, so before `setup`
or `start` you should stage a native Starbound server tree containing
`linux64/starbound_server` inside your chosen `<install_dir>/`.

Start it:

```bash
alphagsm mystarboun start
```

Check it:

```bash
alphagsm mystarboun status
```

Stop it:

```bash
alphagsm mystarboun stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

Suggested flow:

```bash
alphagsm mystarboun create starbound
alphagsm mystarboun setup -n /path/to/starbound
# copy linux64/starbound_server and the rest of the native server tree into /path/to/starbound/
alphagsm mystarboun start
```

## Useful Commands

```bash
alphagsm mystarboun update
alphagsm mystarboun backup
```

## Notes

- Module name: `starbound`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `linux64/starbound_server`
- **Location**: `<install_dir>/linux64/starbound_server`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `211820`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/starbound/](../server-templates/starbound/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
