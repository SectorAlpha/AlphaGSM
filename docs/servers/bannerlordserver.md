# Mount & Blade II: Bannerlord

This guide covers the `bannerlordserver` module in AlphaGSM.

## Support Status

`bannerlordserver` is supported in `ENABLED (AUTH)` mode.

AlphaGSM can:

- manage the dedicated server lifecycle
- install the Linux dedicated payload through SteamCMD when authenticated access is available
- launch the Linux server through the shared `steamcmd-linux` Docker runtime

The remaining operator-provided prerequisites are:

- authenticated Steam or SteamCMD access to Bannerlord dedicated server app `1863440` branch `linux_test`
- a TaleWorlds custom server token before `start`

Anonymous SteamCMD is not enough for the supported Linux branch.

## Quick Start

Create the server:

```bash
alphagsm mybannerlo create bannerlordserver
```

Configure SteamCMD credentials in your AlphaGSM user config so `setup` can use an entitled account:

```ini
[downloader.steamcmd]
username = YOUR_STEAM_USERNAME
password = YOUR_STEAM_PASSWORD
```

Run setup:

```bash
alphagsm mybannerlo setup
```

Generate a custom server token from the Bannerlord multiplayer client, then stage it where the dedicated server can use it, or pass it through the supported launch argument flow described in the official TaleWorlds hosting guide.

Start it:

```bash
alphagsm mybannerlo start
```

Check it:

```bash
alphagsm mybannerlo status
```

Stop it:

```bash
alphagsm mybannerlo stop
```

## Requirements

- Docker for the supported Linux runtime path
- SteamCMD
- authenticated Steam or SteamCMD access to Bannerlord dedicated server app `1863440` branch `linux_test`
- a TaleWorlds custom server token generated from an owned Bannerlord multiplayer account

## Setup Details

Setup configures:

- the game port
- the install directory
- the Linux dedicated branch `linux_test` from Steam app `1863440`
- the Linux starter under `bin/Linux64_Shipping_Server/`

## TaleWorlds Custom Server Token

Bannerlord dedicated hosting requires a custom server token tied to a Bannerlord account.

The official TaleWorlds flow is:

1. Launch Bannerlord multiplayer and log in.
2. Open the in-game console.
3. Run `customserver.gettoken`.
4. Copy the generated token to the host that will run the dedicated server, or pass it on launch with `/dedicatedcustomserverauthtoken`.

The token expires periodically, so replace it when TaleWorlds rotates it.

## Useful Commands

```bash
alphagsm mybannerlo update
alphagsm mybannerlo backup
```

## Notes

- Module name: `bannerlordserver`
- Steam App ID: `1863440`
- Steam branch: `linux_test`
- Default port: `7210`
- Default executable: `bin/Linux64_Shipping_Server/TaleWorlds.Starter.DotNetCore.Linux.dll`

## Developer Notes

### Run File

- **Executable**: `TaleWorlds.Starter.DotNetCore.Linux.dll`
- **Location**: `<install_dir>/bin/Linux64_Shipping_Server/TaleWorlds.Starter.DotNetCore.Linux.dll`
- **Engine**: `.NET` Linux dedicated server started through `dotnet`
- **SteamCMD App ID**: `1863440`
- **Steam branch**: `linux_test`

### Runtime Notes

- The supported Linux lane is the module's `steamcmd-linux` Docker runtime contract.
- The validated setup blocker is no longer a missing `dotnet` runtime. The real gating requirement is access to the authenticated `linux_test` branch plus a valid custom server token.
