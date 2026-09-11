# BungeeCord

This guide covers the `minecraft.bungeecord` module in AlphaGSM.

`minecraft.bungeecord` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- Java 17 or compatible runtime
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

- the game port (default 25565)
- the install directory
- downloads the BungeeCord proxy jar automatically

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
- Default port: 25565

<!-- alphagsm-server-variables:start -->

## Server variables

After `create minecraft.bungeecord`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `BungeeCord.jar`
- **Location**: `<install_dir>/BungeeCord.jar`
- **Engine**: Java (BungeeCord proxy)

### Server Configuration

- **Config file**: `config.yml`
- **Key settings** (in `config.yml`):
  - `listeners[0].host` — Proxy bind host and port
  - `listeners[0].motd` — Message of the day
  - `listeners[0].max_players` — Maximum players shown in server ping
  - `servers` — Downstream backend server definitions
  - `motd` — Message of the day
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-bungeecord/](../server-templates/minecraft-bungeecord/) if available

By default AlphaGSM resolves the latest successful upstream BungeeCord Jenkins
build and downloads `BungeeCord.jar` automatically during `setup`. You can also
override that with `--version <build-number>` or `--url <jar-url>`.

### Maps and Mods

- **Map directory**: `N/A (proxy)`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: BungeeCord is a proxy and does not host worlds.
- **Mod notes**: AlphaGSM can install built-in manifest families such as `viaversion`, `viabackwards`, `viarewind`, `luckperms`, and `geyser`, place plugin `.jar` files from direct URLs into `plugins/`, and install Mod DB-backed archives when they contain plugin payloads under approved proxy plugin paths. `mod cleanup` removes only AlphaGSM-managed plugin files. The checked-in manifest now auto-installs ViaVersion-stack prerequisites when needed and selects the Bungee-compatible jar for variant-specific families. BungeeCord keeps its own cache/state under `.alphagsm/mods/minecraft-bungeecord/`.
