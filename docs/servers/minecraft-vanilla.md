# Minecraft Vanilla

This guide is for running a normal vanilla Minecraft server with AlphaGSM.

## What You Need

- Java 21 or another compatible Java runtime
- `screen`
- the Python packages in `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymc create minecraft.vanilla
```

Run setup:

```bash
alphagsm mymc setup
```

Start it:

```bash
alphagsm mymc start
```

Check it:

```bash
alphagsm mymc status
```

Stop it:

```bash
alphagsm mymc stop
```

## What Setup May Ask For

- the Minecraft version
- a download URL
- the port
- where to install the server
- where Java is installed

## Useful Commands

```bash
alphagsm mymc message "hello world"
alphagsm mymc backup
```

## Best Working Example

The best full example in the repository is:

- `tests/smoke_tests/run_minecraft_vanilla.sh`

It uses this command flow:

```bash
alphagsm itmc create minecraft.vanilla
alphagsm itmc set javapath /path/to/java-wrapper.sh
alphagsm itmc setup -n -l PORT /tmp/minecraft-server -u SERVER_URL
alphagsm itmc start
alphagsm itmc status
alphagsm itmc message "hello world"
alphagsm itmc stop
alphagsm itmc status
```

## Notes

- `minecraft` is the short name people usually type.
- `minecraft.vanilla` is the full module name.
- If you want the most realistic example, follow the smoke test.

## Developer Notes

### Run File

- **Executable**: `minecraft_server.jar`
- **Location**: `<install_dir>/minecraft_server.jar`
- **Engine**: Java (Mojang)

### Server Configuration

- **Config file**: `server.properties`
- **Key settings** (in `server.properties`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-vanilla/](../server-templates/minecraft-vanilla/) if available

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `Not supported (vanilla)`
- **Workshop support**: No
- **Map notes**: The world directory contains all world data. Delete it to regenerate.
- **Mod notes**: Vanilla servers do not support mods. Use Paper or Forge for mod support.
