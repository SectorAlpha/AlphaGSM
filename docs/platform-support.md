# Platform Support

This file explains how to read AlphaGSM game server platform support.

AlphaGSM itself is Linux-first. Most modules are written with a Linux host in mind, but some game
servers still ship Windows-oriented dedicated server binaries, community server wrappers, or
owned-game/manual startup scripts.

## How To Read This

If a module is not called out in the Windows-oriented or manual/community exception tables below,
the current default assumption is:

| Module type | Linux host | Windows host | Notes |
| --- | --- | --- | --- |
| Standard AlphaGSM game module | Yes | Not a current target | Linux is the primary supported host for AlphaGSM itself. |

## Support Classes

| Support class | Linux host | Windows host | Meaning |
| --- | --- | --- | --- |
| Linux-first native/server-script module | Yes | Not tracked | The module starts a Linux launcher, shell script, Java jar, or native binary. |
| Windows-oriented dedicated server binary | Partial / needs compatibility review | Not tracked by AlphaGSM | The game server is modeled in AlphaGSM, but the shipped launcher is a `.exe`, `.bat`, or `.ps1`. These modules exist, but deeper runtime validation may still be needed. |
| Manual or owned-game server files | Partial / user-supplied files | Not tracked by AlphaGSM | The module expects server files that come from an owned game install, a manual archive, or a custom/community package. |
| Community server wrapper | Partial / community-maintained | Not tracked by AlphaGSM | The module is useful, but it is not based on a first-party dedicated server package. |

## Windows-Oriented Modules

These modules currently default to Windows-style launch artifacts such as `.exe`, `.bat`, or
`.ps1`.

| Family | Module ids | Default launcher style |
| --- | --- | --- |
| Survival and sandbox | `accserver`, `aloftserver`, `arksurvivalascended`, `askaserver`, `astroneerserver`, `battlecryoffreedomserver`, `darkandlightserver`, `empyrionserver`, `fearthenightserver`, `heatserver`, `hellletlooseserver`, `icarusserver`, `lifeisfeudalserver`, `medievalengineersserver`, `miscreatedserver`, `motortownserver`, `mythofempiresserver`, `noonesurvivedserver`, `notdserver`, `outpostzeroserver`, `pixarkserver`, `remnantsserver`, `returntomoriaserver`, `reignofdwarfserver`, `scumserver`, `sonsoftheforestserver`, `sunkenlandserver`, `terratechworldsserver`, `theforestserver` | `.exe`, `.bat`, or `.ps1` |
| Tactical and shooter | `blackops3server`, `blackwakeserver`, `groundbranchserver`, `mw3server`, `readyornotserver`, `rs2server`, `sniperelite4server` | `.exe` |
| Racing and vehicle | `stormworksserver`, `staxelserver` | `.exe` |
| Misc provider-style and community targets | `hogwarpserver`, `reignofkingsserver` | `.exe` |

## Manual Or Owned-Game Modules

These modules do not currently represent a normal anonymous dedicated server download path.

| Module id | Linux host | Windows host | Notes |
| --- | --- | --- | --- |
| `aloftserver` | Partial | Not tracked | Uses owned-game server scripts and currently starts `AloftServerNoGuiLoad.ps1` through `pwsh`. |
| `gravserver` | Partial | Not tracked | Uses owned-game or manually supplied GRAV server files. |
| `trackmaniaserver` | Partial | Not tracked | Uses a direct archive/manual download flow for the dedicated server package. |
| `hogwarpserver` | Partial | Not tracked | Uses a direct archive/manual download flow for the community server package. |
| `gtafivemserver` | Partial | Not tracked | Uses manual archive/server artifact flow rather than SteamCMD. |
| `redmserver` | Partial | Not tracked | Uses manual archive/server artifact flow rather than SteamCMD. |

## Community Server Modules

These are useful AlphaGSM modules, but they are not based on a first-party dedicated server binary.

| Module id | Linux host | Windows host | Notes |
| --- | --- | --- | --- |
| `subnauticaserver` | Partial | Not tracked | Uses the Nitrox community server. |
| `kerbalspaceprogramserver` | Partial | Not tracked | Uses the LunaMultiplayer community server. |
| `skyrimtogetherrebornserver` | Partial | Not tracked | Community multiplayer server target. |
| `rimworldtogetherserver` | Partial | Not tracked | Community multiplayer server target. |
| `hogwarpserver` | Partial | Not tracked | Community server package for Hogwarts Legacy multiplayer. |

## Linux-First Examples

These are representative modules that currently look Linux-native in their default launcher shape.

| Family | Examples |
| --- | --- |
| Minecraft and Terraria | `minecraft.vanilla`, `minecraft.paper`, `minecraft.velocity`, `minecraft.waterfall`, `minecraft.bedrock`, `terraria.vanilla`, `terraria.tshock` |
| Valve family | `teamfortress2`, `cssserver`, `csserver`, `l4d2server`, `gmodserver`, `nmrihserver`, `zpsserver`, `svenserver` |
| Survival and sandbox | `ark`, `rust`, `valheim`, `starbound`, `projectzomboid`, `satisfactory`, `palworld`, `nightingale`, `smallandserver`, `sevendaystodie`, `unturned` |
| Tactical and modern shooter | `squadserver`, `squad44server`, `ohdserver`, `exfilserver`, `pvrserver` |
| Racing and misc | `atsserver`, `ets2server`, `avserver`, `mordserver`, `stationeersserver`, `veinserver` |

## Notes

| Topic | Note |
| --- | --- |
| Host operating system | AlphaGSM is still a Linux-first project. |
| Windows-only launchers | A Windows-oriented module being present does not automatically mean full runtime validation has been done on a Linux host. |
| Tracker usage | Use this file alongside [Game Server Support](game-server-support.md) when deciding whether a server is implemented, blocked, or still needs deeper runtime validation. |
