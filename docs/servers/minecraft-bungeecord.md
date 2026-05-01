# Collect and store configuration values for a Bungeecord

This guide covers the `minecraft.bungeecord` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybungeeco create minecraft.bungeecord
```

Run setup:

```bash
alphagsm mybungeeco setup
```

Start it:

```bash
alphagsm mybungeeco start
```

Check it:

```bash
alphagsm mybungeeco status
```

Stop it:

```bash
alphagsm mybungeeco stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm mybungeeco update
alphagsm mybungeeco backup
```

Built-in manifest plugin families, direct plugin jars, and provider-hosted
plugin archives can all be managed through AlphaGSM:

```bash
alphagsm mybungeeco mod add manifest viaversion
alphagsm mybungeeco mod add manifest viabackwards
alphagsm mybungeeco mod add manifest viarewind
alphagsm mybungeeco mod add manifest luckperms
alphagsm mybungeeco mod add manifest geyser
alphagsm mybungeeco mod add url https://plugins.example.invalid/TestPlugin.jar
alphagsm mybungeeco mod add moddb https://www.moddb.com/mods/proxy-pack/downloads/proxy-pack
alphagsm mybungeeco mod apply
alphagsm mybungeeco mod cleanup
```

## Notes

- Module name: `minecraft.bungeecord`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `BungeeCord.jar`
- **Location**: `<install_dir>/BungeeCord.jar`
- **Engine**: Java (BungeeCord proxy)

### Server Configuration

- **Config file**: `config.yml`
- **Key settings** (in `config.yml`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-bungeecord/](../server-templates/minecraft-bungeecord/) if available

### Maps and Mods

- **Map directory**: `N/A (proxy)`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: BungeeCord is a proxy and does not host worlds.
- **Mod notes**: AlphaGSM can install built-in manifest families such as `viaversion`, `viabackwards`, `viarewind`, `luckperms`, and `geyser`, place plugin `.jar` files from direct URLs into `plugins/`, and install Mod DB-backed archives when they contain plugin payloads under approved proxy plugin paths. `mod cleanup` removes only AlphaGSM-managed plugin files. The checked-in manifest now auto-installs ViaVersion-stack prerequisites when needed and selects the Bungee-compatible jar for variant-specific families. BungeeCord keeps its own cache/state under `.alphagsm/mods/minecraft-bungeecord/`.
