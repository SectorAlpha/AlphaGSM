# Terraria tModLoader

tModLoader hosts multiplayer Terraria worlds with server-compatible mods. AlphaGSM installs the official public GitHub release and uses direct IP connections without a Steam client login.

```bash
alphagsm mytml create terraria.tmodloader
alphagsm mytml setup -n 7777 ~/mytml
alphagsm mytml start --autocreate
alphagsm mytml status
alphagsm mytml query
alphagsm mytml info --json
alphagsm mytml stop
```

Use `--autocreate` to create the configured world when it is missing. Existing worlds are retained. Players need a matching Terraria/tModLoader version and the server's mods.

For a specific official release, add `--version v2026.08.3.0` to setup. `update` follows the selected release; installations using the default latest release follow upstream stable releases.

## Workshop mods

Stop the server before changing mods. For example, Census provides a multiplayer-compatible town NPC checklist and its own server console command:

```bash
alphagsm mytml mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=2687866031
alphagsm mytml mod apply
alphagsm mytml start --autocreate
alphagsm mytml send TownProgress
```

Items and collections both accept numeric IDs or official Workshop URLs:

```bash
alphagsm mytml mod add workshop-collection COLLECTION_ID_OR_URL
alphagsm mytml mod list
alphagsm mytml mod remove workshop ITEM_ID_OR_URL
alphagsm mytml mod apply
alphagsm mytml mod cleanup
```

AlphaGSM checks every collection member against tModLoader's game AppID `1281930`, downloads anonymously, verifies TMOD package hashes and internal paths, and selects the latest compatible package for the installed release. Its adapter targets the 1.4.4 mod format. Use mods marked **Both** or **Server**, and add their required dependencies explicitly. Client-only features cannot establish server support.

Managed packages go in `Mods/<internal-mod-name>.tmod`; enabled names are maintained in `Mods/enabled.json`. Existing operator mod names are preserved. AlphaGSM refuses to replace unowned packages or delete externally edited managed packages. Cleanup removes owned packages and enabled entries while retaining download caches, worlds and operator content. `mod list` reports configuration, not proof that the engine loaded a mod.

## Settings and files

- Game port: TCP `7777` by default.
- Configuration: `serverconfig.txt`; `set` synchronizes declared gameplay settings.
- Worlds: `Worlds/`; native mod save data: `Saved/`; manual mods: `Mods/`.
- Backups include worlds, saves, mods and server configuration.
- Query/info use Terraria's framed native handshake.
- Docker uses the shared `steamcmd-linux` runtime family and the same native launcher.

The upstream launcher installs its required .NET runtime on first startup, so startup needs internet access and can take longer than subsequent launches.

## Validation

The integration cases drive create, setup, start, readiness, status, query, info, info JSON, stop and shutdown through AlphaGSM for process and Docker runtimes. The opt-in Workshop case requires fresh output from Census's actual `TownProgress` command, rather than accepting a downloaded file or enabled JSON entry as load evidence.

```bash
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 ALPHAGSM_RUN_WORKSHOP=1 \
  python -m pytest tests/integration_tests/test_terraria_tmodloader.py -v
```

Process and branch-local Docker validation passed on tModLoader `v2026.08.3.0`: both baseline and Workshop lifecycles succeeded, and Census executed its own server console command in each Workshop case. These checks prove mod loading and command execution, not every gameplay feature.

Sources: [upstream server guide](https://github.com/tModLoader/tModLoader/wiki/Starting-a-modded-server), [release assets](https://github.com/tModLoader/tModLoader/releases), [Census Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=2687866031).
