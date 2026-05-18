# Unreal Tournament 3

This guide covers the `ut3server` module in AlphaGSM.

## Requirements

- `screen`
- user-provided Unreal Tournament 3 dedicated server files
- OpenSpy credentials if you want the server to authenticate and advertise

## Quick Start

```bash
alphagsm myut3 create ut3server
alphagsm myut3 setup
alphagsm myut3 start
alphagsm myut3 status
alphagsm myut3 stop
```

## Notes

- Module name: `ut3server`
- Install mode: bring-your-own server files
- Default port: `7777`
- Default query port: `6500`
- Query/info protocol: `ut3` (Unreal3/GameSpy4 reachability probe)

## Developer Notes

- AlphaGSM expects the server executable at `Binaries/ut3` relative to the install root.
- The start surface follows LinuxGSM's UT3 launch pattern, including `ConfigSubDir=<server-name>`, `-queryport`, `-nohomedir`, and `-unattended`.
- The active config path defaults to `UTGame/Config/<server-name>/UTGame.ini`.
- Automated install is not provided because LinuxGSM does not expose a concrete upstream download path for UT3; this module manages user-provided files instead.