# minecraft.waterfall

This guide covers the `minecraft.waterfall` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywaterfal create minecraft.waterfall
```

Run setup:

```bash
alphagsm mywaterfal setup
```

Start it:

```bash
alphagsm mywaterfal start
```

Check it:

```bash
alphagsm mywaterfal status
```

Stop it:

```bash
alphagsm mywaterfal stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

## Useful Commands

```bash
alphagsm mywaterfal update
alphagsm mywaterfal backup
```

Built-in manifest plugin families, direct plugin jars, and provider-hosted
plugin archives can all be managed through AlphaGSM:

```bash
alphagsm mywaterfal mod add manifest viaversion
alphagsm mywaterfal mod add manifest viabackwards
alphagsm mywaterfal mod add manifest viarewind
alphagsm mywaterfal mod add manifest luckperms
alphagsm mywaterfal mod add manifest geyser
alphagsm mywaterfal mod add url https://plugins.example.invalid/TestPlugin.jar
alphagsm mywaterfal mod add moddb https://www.moddb.com/mods/proxy-pack/downloads/proxy-pack
alphagsm mywaterfal mod apply
alphagsm mywaterfal mod cleanup
```

## Notes

- Module name: `minecraft.waterfall`
- Default port: 25565

## Developer Notes

### Run File

- **Executable**: `waterfall.jar`
- **Location**: `<install_dir>/waterfall.jar`
- **Engine**: Java (Waterfall proxy)

### Server Configuration

- **Config file**: `config.yml`
- **Key settings** (in `config.yml`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-waterfall/](../server-templates/minecraft-waterfall/) if available

### Maps and Mods

- **Map directory**: `N/A (proxy)`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: Waterfall is a proxy and does not host worlds.
- **Mod notes**: AlphaGSM can install built-in manifest families such as `viaversion`, `viabackwards`, `viarewind`, `luckperms`, and `geyser`, place plugin `.jar` files from direct URLs into `plugins/`, and install Mod DB-backed archives when they contain plugin payloads under approved proxy plugin paths. `mod cleanup` removes only AlphaGSM-managed plugin files. The checked-in manifest now auto-installs ViaVersion-stack prerequisites when needed and selects the Bungee-compatible jar for variant-specific families. Waterfall keeps its own cache/state under `.alphagsm/mods/minecraft-waterfall/`.
