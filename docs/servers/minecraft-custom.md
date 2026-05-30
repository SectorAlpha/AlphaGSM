# Common Minecraft

This guide covers the `minecraft.custom` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycustom create minecraft.custom
```

Run setup:

```bash
alphagsm mycustom setup
```

Start it:

```bash
alphagsm mycustom start
```

Check it:

```bash
alphagsm mycustom status
```

Stop it:

```bash
alphagsm mycustom stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

`minecraft.custom` is a bring-your-own-jar lane. AlphaGSM does not know which
custom server binary you want by default, so `setup` only succeeds after you
provide the jar yourself.

Supported operator workflow:

1. create the server
2. choose the jar filename AlphaGSM should execute
3. copy the real server jar into the install directory
4. rerun `setup`
5. start the server normally

Example:

```bash
alphagsm mycustom create minecraft.custom
alphagsm mycustom set exe_name paper-1.21.1.jar
mkdir -p /srv/alphagsm/mycustom
cp /path/to/paper-1.21.1.jar /srv/alphagsm/mycustom/
alphagsm mycustom setup 25565 /srv/alphagsm/mycustom
alphagsm mycustom start
```

If `setup` says `Can't find server jar (...)`, the fix is to place the jar at
`<install_dir>/<exe_name>` or update `exe_name` and run `setup` again.

## Useful Commands

```bash
alphagsm mycustom update
alphagsm mycustom backup
alphagsm mycustom set gamemap CustomWorld
alphagsm mycustom set servername "AlphaGSM Custom Server"
alphagsm mycustom set exe_name paper-1.21.1.jar
```

## Notes

- Module name: `minecraft.custom`
- Default port: 25565

## Developer Notes

### Run File

- **Executable**: `custom .jar (user-specified)`
- **Location**: `<install_dir>/<exe_name>`
- **Engine**: Java (Custom)

### Server Configuration

- **Config file**: `server.properties`
- **Key settings** (in `server.properties`):
  - `server-port` — Game port (default 25565)
  - `level-name` — World name managed by `set gamemap`
  - `motd` — Message of the day, managed by `set servername`
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-custom/](../server-templates/minecraft-custom/) if available

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `mods/ or plugins/ (depends on server type)`
- **Workshop support**: No
- **Map notes**: The world directory contains all world data.
- **Mod notes**: Depends on the custom server type (Forge, Fabric, Spigot, etc.).
