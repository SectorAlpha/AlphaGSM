# TShock

This guide covers the `terraria.tshock` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytshock create terraria.tshock
```

Run setup:

```bash
alphagsm mytshock setup
```

Start it:

```bash
alphagsm mytshock start
```

Check it:

```bash
alphagsm mytshock status
```

Stop it:

```bash
alphagsm mytshock stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mytshock update
alphagsm mytshock backup
```

## Notes

- Module name: `terraria.tshock`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `TShock.Server.dll`
- **Location**: `<install_dir>/TShock.Server.dll`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/terraria-tshock/](../server-templates/terraria-tshock/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: `ServerPlugins/`
- **Workshop support**: No

## Plugin Sources

TShock plugin management is separate from vanilla Terraria and uses its own
AlphaGSM cache/state root.

- AlphaGSM stores TShock plugin cache/state under `.alphagsm/mods/terraria-tshock/` so it does not collide with other Terraria variants.
- Current plugin source support is `manifest`, `url`, and `moddb`.
- `manifest` uses AlphaGSM's checked-in TShock plugin registry. The built-in families currently include `banguard`, `smartregions`, `omni`, `perplayerloot`, `autoteam`, `facommands`, `timeranks`, `ranksystem`, `qol`, `replenisher`, `bagger`, and `tslootchest`.
- `url` accepts direct plugin `.dll` downloads and `.zip` plugin packages, including release zips that expose a bare plugin root instead of a prebuilt `ServerPlugins/` directory.
- `moddb` accepts canonical Mod DB download or addon page URLs when the resolved payload contains TShock plugin files under `ServerPlugins/`, `tshock/`, or as a bare plugin-root archive.
- AlphaGSM records installed plugin files per entry so `mod cleanup` removes only tracked plugins and leaves unrelated files alone.

Examples:

```bash
alphagsm mytshock mod add manifest banguard
alphagsm mytshock mod add manifest smartregions
alphagsm mytshock mod add manifest perplayerloot
alphagsm mytshock mod add manifest timeranks
alphagsm mytshock mod add manifest tslootchest
alphagsm mytshock mod apply
alphagsm mytshock mod cleanup
```

```bash
alphagsm mytshock mod add url https://plugins.example.invalid/ExamplePlugin.dll
alphagsm mytshock mod apply
alphagsm mytshock mod cleanup
```

```bash
alphagsm mytshock mod add moddb https://www.moddb.com/mods/example/downloads/example-plugin-pack
alphagsm mytshock mod apply
alphagsm mytshock mod cleanup
```
