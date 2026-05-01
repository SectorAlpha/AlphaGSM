# minecraft.paper

This guide covers the `minecraft.paper` module in AlphaGSM.

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

## Useful Commands

```bash
alphagsm mypaper update
alphagsm mypaper backup
```

## Notes

- Module name: `minecraft.paper`
- Default port: 25565

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
