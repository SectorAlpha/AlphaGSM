# Quake 2

This guide covers the `q2server` module in AlphaGSM.

`q2server` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server currently
follows the native Linux direct-download and source-build Yamagi Quake II
lifecycle, with demo `baseq2` content and Quake II `status` validation.

## Requirements

- `gcc`
- `make`
- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq2server create q2server
```

Run setup:

```bash
alphagsm myq2server setup
```

Start it:

```bash
alphagsm myq2server start
```

Check it:

```bash
alphagsm myq2server status
```

Stop it:

```bash
alphagsm myq2server stop
```

## Setup Details

Setup configures:

- the game port (default 27910)
- the install directory
- downloads the official Yamagi Quake II source archive and builds `release/q2ded`
- builds `release/baseq2/game.so`
- bootstraps the official Quake II demo `baseq2` data so a fresh install can start anonymously
- uses `demo1` as the default start map on fresh demo-backed installs

AlphaGSM launches Yamagi with `-portable`, keeping generated server data in
the installation directory for both process and Docker runtimes. This avoids
startup failures when the operating-system user's XDG data directory does not
exist or is not writable. CI validation of this startup fix is pending.

## Useful Commands

```bash
alphagsm myq2server update
alphagsm myq2server backup
alphagsm myq2server set servername "AlphaGSM Q2"
alphagsm myq2server set gamedir custom
alphagsm myq2server set map demo2
```

`set servername`, `set gamedir`, and `set map` rewrite `<gamedir>/server.cfg` immediately through the schema-backed config-sync path.

If you later add the full retail `baseq2/pak0.pak` content, you can switch to retail multiplayer maps such as `q2dm1` with `set map q2dm1`.

## Notes

- Module name: `q2server`
- Default port: 27910
- Fresh-install default map: `demo1`

## Developer Notes

### Run File

- **Executable**: `release/q2ded`
- **Location**: `<install_dir>/release/q2ded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<gamedir>/server.cfg` (default `baseq2/server.cfg`)
- **Schema-backed sync**: AlphaGSM keeps `hostname`, `gamedir`, and `startmap` aligned with `set`
- **Template**: See [server-templates/q2server/](../server-templates/q2server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<gamedir>/`
- **Mod directory**: `<install_dir>/<gamedir>/`
- **Workshop support**: No
- **Fresh install content**: AlphaGSM stages the official Quake II demo `baseq2` data so anonymous installs can start and answer query/info without retail files

## Mod Sources

Quake 2 supports AlphaGSM-managed direct `url` mod sources for content-only `.pak` payloads.

Supported payload shapes:

- a direct `.pak` URL
- an archive containing bare `.pak` files at the archive root
- an archive containing `<gamedir>/<name>.pak`

AlphaGSM installs approved `.pak` content into the active `gamedir`, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm myq2server mod add url https://example.com/pak1.pak
alphagsm myq2server mod add url https://example.com/custom-content.zip
alphagsm myq2server mod apply
alphagsm myq2server mod cleanup
```
