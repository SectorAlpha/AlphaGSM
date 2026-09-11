# BattleBit Remastered

This guide covers the `battlebitserver` module in AlphaGSM.

## Support Status

`battlebitserver` is supported in `ENABLED (AUTH)` mode.

AlphaGSM can:

- install the BattleBit dedicated payload anonymously from SteamCMD app `689410`
- manage the Linux runtime through the shared Docker-backed `wine-proton` lane
- start the real Windows dedicated binary `BattleBit.exe`

The remaining prerequisite is provider-backed BattleBit community-server
provisioning. Before `start`, you must provide:

- `apiendpoint` set to the BattleBit community-server API host:port
- optionally `apitoken` if your community-server API requires token-based verification
- a host that is already approved for BattleBit community-server hosting under the current BattleBit agreement/TOS flow

## Quick Start

Create the server:

```bash
alphagsm mybattlebi create battlebitserver
```

Run setup:

```bash
alphagsm mybattlebi setup
```

Set the required BattleBit community-server API endpoint:

```bash
alphagsm mybattlebi set apiendpoint HOST_OR_IP:PORT
```

If your provider flow requires a token, set it too:

```bash
alphagsm mybattlebi set apitoken YOUR_OPTIONAL_API_TOKEN
```

Start it:

```bash
alphagsm mybattlebi start
```

Check it:

```bash
alphagsm mybattlebi status
```

Stop it:

```bash
alphagsm mybattlebi stop
```

## Requirements

- Docker for the supported Linux runtime path
- SteamCMD
- BattleBit community-server provisioning/approval
- a reachable BattleBit community-server API endpoint

## Setup Details

Setup configures:

- the main game port (default `29992`)
- the install directory
- the Windows dedicated payload from Steam app `689410`

The supported Linux path then runs `BattleBit.exe` under the shared
`wine-proton` runtime.

## Provider Prerequisites

BattleBit now installs anonymously, but a fresh server still will not boot
through AlphaGSM without a real community-server API endpoint.

AlphaGSM expects:

- `apiendpoint`
- optional `apitoken`

Set them with:

```bash
alphagsm mybattlebi set apiendpoint HOST_OR_IP:PORT
alphagsm mybattlebi set apitoken YOUR_OPTIONAL_API_TOKEN
```

If `apiendpoint` is missing, AlphaGSM fails fast at `start` with an
`ENABLED (AUTH)` message instead of pretending the server is unsupported.

## Useful Commands

```bash
alphagsm mybattlebi update
alphagsm mybattlebi backup
alphagsm mybattlebi set apiendpoint HOST_OR_IP:PORT
alphagsm mybattlebi set apitoken YOUR_OPTIONAL_API_TOKEN
```

## Notes

- Module name: `battlebitserver`
- Steam App ID: `689410`
- Default game port: `29992`
- Default executable: `BattleBit.exe`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create battlebitserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `apiendpoint` | — | string | BattleBit community server API endpoint in host:port form. |
| `apitoken` | — | string | Optional BattleBit community server API token. Stored as a secret. |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `maxplayers` | users | integer | The maximum number of players. |
| `port` | gameport | integer | The game port for the BattleBit community server. |
| `servername` | name, hostname | string | The advertised BattleBit community server name. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `BattleBit.exe`
- **Location**: `<install_dir>/BattleBit.exe`
- **Engine**: Windows dedicated payload run through the shared Wine/Proton runtime on Linux
- **SteamCMD App ID**: `689410`

### Runtime Notes

- The old “missing Linux dedicated binary” disabled note was stale: the anonymous payload is real, but it is Windows-only.
- The supported Linux contract is the shared Docker-backed `wine-proton` runtime, not a fake native binary.
- BattleBit community-server provisioning remains the blocker to a fully green automated lifecycle.
