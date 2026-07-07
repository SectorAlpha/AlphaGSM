# Unreal Tournament 3

This guide covers the `ut3server` module in AlphaGSM.

`ut3server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that owned-dedicated-tree prerequisite, while
local runs remain process-backed by default unless you opt into the Docker
backend.

## Requirements

- `screen`
- an owned Unreal Tournament 3 dedicated-server tree
- optional OpenSpy credentials if you want the server to authenticate and advertise

## Quick Start

```bash
alphagsm myut3 create ut3server
alphagsm myut3 setup
alphagsm myut3 start
alphagsm myut3 status
alphagsm myut3 stop
```

`ut3server` is supported in `ENABLED (BYO)` mode. Before `setup` or `start`,
copy an owned UT3 dedicated server tree into your chosen `<install_dir>/` so
`<install_dir>/Binaries/ut3` exists. If you want authenticated public
advertising, set `gsusername` and `gspassword` with your OpenSpy credentials
before starting the server.

Suggested flow:

```bash
alphagsm myut3 create ut3server
alphagsm myut3 setup -n 7777 /path/to/ut3server
# copy the owned UT3 dedicated server files into /path/to/ut3server/
alphagsm myut3 set gsusername myopenspyuser
alphagsm myut3 set gspassword myopenspypassword
alphagsm myut3 start
```

## Notes

- Module name: `ut3server`
- Install mode: ENABLED (BYO) server files
- Default port: `7777`
- Default query port: `6500`
- Query/info protocol: `ut3` (Unreal3/GameSpy4 reachability probe)

## Developer Notes

- AlphaGSM expects the server executable at `Binaries/ut3` relative to the install root.
- The start surface follows LinuxGSM's UT3 launch pattern, including `ConfigSubDir=<server-name>`, `-queryport`, `-nohomedir`, and `-unattended`.
- The active config path defaults to `UTGame/Config/<server-name>/UTGame.ini`.
- Automated install is not provided because LinuxGSM does not expose a concrete upstream download path for UT3; this module manages user-provided files instead.
