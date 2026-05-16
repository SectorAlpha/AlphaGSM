# SCP: Secret Laboratory

This guide covers the `scpslserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myscpslser create scpslserver
```

Run setup:

```bash
alphagsm myscpslser setup
```

Start it:

```bash
alphagsm myscpslser start
```

Check it:

```bash
alphagsm myscpslser status
```

Stop it:

```bash
alphagsm myscpslser stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default `port + 1`)
- the install directory
- optional `contactemail` for the public-list contact field
- SteamCMD downloads the server files

The canonical gameplay/query settings are managed with `set`:

```bash
alphagsm myscpslser set servername "AlphaGSM SCP:SL Server"
alphagsm myscpslser set queryport 7778
alphagsm myscpslser set rconpassword "changeme"
```

`query_port_shift` is derived automatically as `queryport - port` when AlphaGSM writes `config_gameplay.txt`, so it updates whenever either port changes.

## Useful Commands

```bash
alphagsm myscpslser update
alphagsm myscpslser backup
```

## Notes

- Module name: `scpslserver`
- Default port: 7777
- AlphaGSM launches SCP:SL through `LocalAdmin`, not by invoking `SCPSL.x86_64` directly
- AlphaGSM seeds `home/.config/SCP Secret Laboratory/` inside the server install so the EULA/config wizard stays noninteractive
- Query is enabled in the generated gameplay config, and `query_port_shift` is derived from the current `queryport - port`

## Developer Notes

### Run File

- **Executable**: `LocalAdmin`
- **Location**: `<install_dir>/LocalAdmin`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `996560`

### Server Configuration

- **Config root**: `<install_dir>/home/.config/SCP Secret Laboratory/`
- **Gameplay config**: `<install_dir>/home/.config/SCP Secret Laboratory/config/<port>/config_gameplay.txt`
- **Canonical set keys**: `servername`, `contactemail`, `queryport`, `rconpassword`
- **Optional property**: `contactemail` maps to SCP:SL `contact_email`
- **Derived query setting**: `queryport` maps to SCP:SL `query_port_shift` via `queryport - port`
- **Template**: See [server-templates/scpslserver/](../server-templates/scpslserver/) if available
- **Current status**: The dedicated server can be launched headlessly on Linux through `LocalAdmin` once its EULA/config state is preseeded.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: `home/.config/SCP Secret Laboratory/LabAPI/plugins/`
- **Dependency directory**: `home/.config/SCP Secret Laboratory/LabAPI/dependencies/`
- **Workshop support**: No

## Plugin Sources

AlphaGSM's current SCP:SL plugin support targets the official LabAPI loader that ships with modern dedicated-server builds.

- AlphaGSM stores SCP:SL plugin cache/state under `.alphagsm/mods/scpslserver/`.
- Current plugin source support is `manifest` and `url`.
- `manifest` uses AlphaGSM's checked-in SCP:SL plugin registry. Current built-in families are `betterhelpcommand` for BetterHelpCommand-LabAPI, `escapeplan` for EscapePlan, and `respawntimer` for RespawnTimer.
- `url` accepts direct LabAPI plugin `.dll` downloads and supported plugin archives.
- Archive payloads can already be laid out relative to the LabAPI root with `plugins/` and `dependencies/`, or expose a bare plugin-root `.dll` that AlphaGSM stages into `plugins/global/`.
- `mod cleanup` removes only AlphaGSM-tracked LabAPI plugin files and leaves unrelated manual plugins alone.

EXILED is intentionally out of scope for this first slice because it requires a heavier framework bootstrap and managed-assembly patching than the official LabAPI plugin loader.

```bash
alphagsm myscpslser mod add manifest betterhelpcommand
alphagsm myscpslser mod add url https://plugins.example.invalid/ExamplePlugin.dll
alphagsm myscpslser mod apply
alphagsm myscpslser mod cleanup
```
