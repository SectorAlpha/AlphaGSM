# minecraft.paper

This guide covers the `minecraft.paper` module in AlphaGSM.

`minecraft.paper` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypaper create minecraft.paper
```

Run setup:

```bash
alphagsm mypaper setup
```

Start it:

```bash
alphagsm mypaper start
```

Check it:

```bash
alphagsm mypaper status
```

Stop it:

```bash
alphagsm mypaper stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

## Resetting the World

Stop the server, then run `alphagsm mymc reset-world` (or `wipe`). AlphaGSM
lists the world data to delete and asks for confirmation. Add `-Y` to skip the
prompt. Run `start` afterwards to generate a fresh world.

See [world creation and reset](../world-management.md) for exactly which files
are removed and the supported layouts.

## Useful Commands

```bash
alphagsm mypaper update
alphagsm mypaper backup
```

## Notes

- Module name: `minecraft.paper`
- Default port: 25565

<!-- alphagsm-server-variables:start -->

## Server variables

After `create minecraft.paper`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `difficulty` | — | string | The world difficulty. Example: `easy`. |
| `gamemode` | — | string | The default game mode. Example: `survival`. |
| `map` | gamemap, level, world, startmap, worldname | string | The selected world or level name. Example: `world`. |
| `maxplayers` | users | integer | The maximum number of players allowed on the server. Example: `20`. |
| `port` | gameport | integer | The port the server listens on. Example: `25565`. |
| `servername` | hostname, name | string | The server name shown in the client list. Example: `AlphaGSM Server`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `paper.jar`
- **Location**: `<install_dir>/paper.jar`
- **Engine**: Java (PaperMC)

### Server Configuration

- **Config file**: `server.properties`
- **Key settings** (in `server.properties`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-paper/](../server-templates/minecraft-paper/) if available

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: The world directory contains all world data. Delete it to regenerate.
- **Mod notes**: AlphaGSM can install built-in manifest families such as `viaversion`, `viabackwards`, `viarewind`, `luckperms`, `vault`, `placeholderapi`, `protocollib`, `essentialsx`, `essentialsxchat`, `essentialsxspawn`, `essentialsxprotect`, `essentialsxantibuild`, and `discordsrv`, track direct plugin jar URLs for Paper, and install Mod DB-backed archives when they expose plugin payloads under approved plugin paths. The checked-in manifest now auto-installs ViaVersion and EssentialsX companion prerequisites when needed.

## Plugin Sources

Paper plugin management is separate from other Minecraft variants.

- AlphaGSM stores Paper plugin cache/state under `.alphagsm/mods/minecraft-paper/` so it does not collide with vanilla, Bedrock, or proxy variants.
- Current plugin source support includes `manifest` for checked-in reproducible plugin families, `url` for direct plugin `.jar` files, and `moddb` for canonical Mod DB page URLs that resolve to provider-hosted plugin archives.
- AlphaGSM records installed plugin files per entry so `mod cleanup` removes only tracked plugins and leaves unrelated files alone.

Examples:

```bash
alphagsm mypaper mod add manifest viaversion
alphagsm mypaper mod add manifest viabackwards
alphagsm mypaper mod add manifest viarewind
alphagsm mypaper mod add manifest luckperms
alphagsm mypaper mod add manifest essentialsxchat
alphagsm mypaper mod add url https://plugins.example.invalid/TestPlugin.jar
alphagsm mypaper mod add moddb https://www.moddb.com/mods/paper-plugin-pack/downloads/paper-plugin-pack
alphagsm mypaper mod apply
alphagsm mypaper mod cleanup
```
