# Longvinter

This guide covers the `longvinterserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylongvint create longvinterserver
```

Run setup:

```bash
alphagsm mylongvint setup
```

Start it:

```bash
alphagsm mylongvint start
```

Check it:

```bash
alphagsm mylongvint status
```

Stop it:

```bash
alphagsm mylongvint stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylongvint update
alphagsm mylongvint backup
```

## Notes

- Module name: `longvinterserver`
- Default port: 7777
- Current CI status: still disabled. Fresh anonymous Linux validation now gets
  through install and launch via `LongvinterServer.sh`, but the packaged server
  exits during EOS startup with `ClientCredentials.ClientId must be an ANSI
  string between 1 and 64 in length` / `EOS_NotConfigured` before any proven
  gameplay or query listener binds.

## Developer Notes

### Run File

- **AlphaGSM executable**: `LongvinterServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1639880`

Current blocker status on 2026-05-29 is now sharper than the older
"stale launcher contract" note:

- the current anonymous Linux payload still launches through the shipped
  `LongvinterServer.sh` wrapper on fresh installs,
- the dedicated server then aborts during EOS platform initialization with
  `ClientCredentials.ClientId must be an ANSI string between 1 and 64 in
  length` and `EOS_NotConfigured`,
- fresh community reports describe the same EOS startup failure across late
  2025 through early 2026.

Until upstream ships a fixed dedicated payload or a documented
credential/bootstrap workaround exists, the disabled gate should stay in place.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/longvinterserver/](../server-templates/longvinterserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
