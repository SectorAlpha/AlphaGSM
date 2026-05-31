# Conan Exiles

This guide covers the `conanexiles` module in AlphaGSM.

Status: `PASSED` on Linux through the shared Docker `wine-proton` runtime.

## Requirements

- Docker if you want the validated Linux runtime path
- SteamCMD access for app `443030` (anonymous download works)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myconan create conanexiles
```

Run setup:

```bash
alphagsm myconan setup
```

Start it:

```bash
alphagsm myconan start
```

Check it:

```bash
alphagsm myconan status
alphagsm myconan query
alphagsm myconan info
```

Stop it:

```bash
alphagsm myconan stop
```

## Setup Details

Setup configures:

- the main game port, default `7777/udp`
- the dedicated query port, default `27015/udp`
- the install directory
- the shipped Windows dedicated payload, which AlphaGSM runs on Linux through the shared `wine-proton` runtime

## Config Files

AlphaGSM manages the normal Conan Exiles server config layout under:

- `<install_dir>/ConanSandbox/Saved/Config/WindowsServer/Engine.ini`
- `<install_dir>/ConanSandbox/Saved/Config/WindowsServer/Game.ini`
- `<install_dir>/ConanSandbox/Saved/Config/WindowsServer/ServerSettings.ini`

Checked-in starter templates live under [docs/server-templates/conanexiles/](../server-templates/conanexiles/).

AlphaGSM keeps these values aligned automatically:

- `port` -> `Engine.ini` `[URL] Port`
- `queryport` -> `Engine.ini` `[OnlineSubsystemNull] GameServerQueryPort`
- `servername` -> `Engine.ini` `[OnlineSubsystem] ServerName`
- `maxplayers` -> `Game.ini` `[/Script/Engine.GameSession] MaxPlayers`

## Runtime Contract

- Preferred executable on Linux: `ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe`
- Query surface: A2S on the managed `queryport`
- Default map: `ConanSandbox`

The game port also exposes gameplay traffic on `port`, and Conan keeps a hardcoded pinger on `port + 1`.

## Useful Commands

```bash
alphagsm myconan set queryport 27015
alphagsm myconan set servername "AlphaGSM Conan"
alphagsm myconan set maxplayers 16
alphagsm myconan update
alphagsm myconan backup
```
