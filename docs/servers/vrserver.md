# V Rising

This guide covers the `vrserver` module in AlphaGSM.

## Support Status

- Status: `PASSED`
- Validated on Linux through the shared Docker `wine-proton` runtime
- Anonymous SteamCMD app id: `1829350`

AlphaGSM now supports V Rising on Linux by installing the Windows dedicated
payload through anonymous SteamCMD and running the real server binary under the
shared Wine/Proton runtime. The validated health surface is generic `udp` on
the managed `queryport`.

## Quick Start

Create the server:

```bash
alphagsm myvrserver create vrserver
```

Run setup:

```bash
alphagsm myvrserver setup
```

Start it:

```bash
alphagsm myvrserver start
```

Check it:

```bash
alphagsm myvrserver query
alphagsm myvrserver info --json
alphagsm myvrserver status
```

Stop it:

```bash
alphagsm myvrserver stop
```

## Setup Details

Setup configures:

- the game port, default `9876`
- the query port, default `9877`
- the install directory
- anonymous SteamCMD download for app `1829350`

On Linux, AlphaGSM uses the shared `wine-proton` Docker runtime for the
supported path.

## Runtime Contract

- Executable: `VRisingServer.exe`
- Working directory: `<install_dir>`
- Persistent data path: `<install_dir>/save-data`
- Managed host settings: `<install_dir>/Settings/ServerHostSettings.json`
- Query/info surface: generic `udp` on `queryport`

Before start, AlphaGSM stages `ServerHostSettings.json` from the checked-in
template and syncs:

- `servername`
- `port`
- `queryport`
- `maxplayers`

The validated launch contract is:

```text
VRisingServer.exe -persistentDataPath <install_dir>/save-data -serverPort <port> -queryPort <queryport>
```

## Useful Commands

```bash
alphagsm myvrserver set servername "My V Rising Server"
alphagsm myvrserver set maxplayers 50
alphagsm myvrserver set queryport 9878
alphagsm myvrserver update
alphagsm myvrserver backup
```

## Notes

- Module name: `vrserver`
- SteamCMD app id: `1829350`
- Supported Linux path: Docker `wine-proton`
