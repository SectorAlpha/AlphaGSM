# HYPERCHARGE: Unboxed

This guide covers the `hcuserver` module in AlphaGSM.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD dependencies from the normal AlphaGSM install path

## Quick Start

```bash
alphagsm myhcu create hcuserver
alphagsm myhcu setup
alphagsm myhcu start
alphagsm myhcu status
alphagsm myhcu stop
```

## Notes

- Module name: `hcuserver`
- LinuxGSM short alias: `hcu`
- Steam app id: `1045940`
- Default port: `7777`
- Query/info protocol: `udp` on the game port

<!-- alphagsm-server-variables:start -->

## Server variables

After `create hcuserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

- AlphaGSM installs the Linux dedicated payload through SteamCMD anonymous login.
- The upstream install ships a launcher script at `UnboxedServer.sh` that wraps `Unboxed/Binaries/Linux/UnboxedServer-Linux-Shipping` and sets Steam server rate-limit environment variables.
- LinuxGSM stores generated config under `Unboxed/Saved/Config/LinuxServer/GameUserSettings.ini` once the server has booted.
- The current Linux dedicated server binds the gameplay socket on `port` and emits a stable readiness marker in `Unboxed/Saved/Logs/Unboxed.log` when `GameNetDriver IpNetDriver listening on port ...` appears.
- In local launch probes the binary did not expose a working A2S query socket or a separate bound `queryport`, so AlphaGSM intentionally uses generic UDP reachability on the gameplay port for `query`, `info`, smoke, and integration coverage.