# minecraft.velocity

This guide covers the `minecraft.velocity` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvelocity create minecraft.velocity
```

Run setup:

```bash
alphagsm myvelocity setup
```

Start it:

```bash
alphagsm myvelocity start
```

Check it:

```bash
alphagsm myvelocity status
```

Stop it:

```bash
alphagsm myvelocity stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

## Useful Commands

```bash
alphagsm myvelocity update
alphagsm myvelocity backup
```

Built-in manifest plugin families, direct plugin jars, and provider-hosted
plugin archives can all be managed through AlphaGSM:

```bash
alphagsm myvelocity mod add manifest viaversion
alphagsm myvelocity mod add manifest viabackwards
alphagsm myvelocity mod add manifest viarewind
alphagsm myvelocity mod add manifest luckperms
alphagsm myvelocity mod add manifest geyser
alphagsm myvelocity mod add url https://plugins.example.invalid/TestPlugin.jar
alphagsm myvelocity mod add moddb https://www.moddb.com/mods/proxy-pack/downloads/proxy-pack
alphagsm myvelocity mod apply
alphagsm myvelocity mod cleanup
```

## Notes

- Module name: `minecraft.velocity`
- Default port: 25565

## Developer Notes

### Run File

- **Executable**: `velocity.jar`
- **Location**: `<install_dir>/velocity.jar`
- **Engine**: Java (Velocity proxy)

### Server Configuration

- **Config file**: `velocity.toml`
- **Key settings** (in `velocity.toml`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-velocity/](../server-templates/minecraft-velocity/) if available

### Maps and Mods

- **Map directory**: `N/A (proxy)`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: Velocity is a proxy and does not host worlds.
- **Mod notes**: AlphaGSM can install built-in manifest families such as `viaversion`, `viabackwards`, `viarewind`, `luckperms`, and `geyser`, place plugin `.jar` files from direct URLs into `plugins/`, and install Mod DB-backed archives when they contain plugin payloads under approved proxy plugin paths. `mod cleanup` removes only AlphaGSM-managed plugin files. The checked-in manifest now auto-installs ViaVersion-stack prerequisites when needed and selects the Velocity-compatible jar for variant-specific families. Velocity keeps its own cache/state under `.alphagsm/mods/minecraft-velocity/`.
