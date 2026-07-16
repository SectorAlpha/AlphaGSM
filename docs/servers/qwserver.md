# QuakeWorld

This guide covers the `qwserver` module in AlphaGSM.

`qwserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server currently
follows the native Linux nQuake and KTX bootstrap lifecycle, with QuakeWorld
`status` validation on the managed server path.

## Requirements

- `screen`
- Python packages from `requirements.txt`
- no Steam login is required; AlphaGSM bootstraps the public nQuake shareware and KTX runtime assets during setup
- an optional `ALPHAGSM_GITHUB_TOKEN` avoids anonymous GitHub API rate limits
  when resolving current MVDSV release metadata; GitHub Actions supplies its
  read-only job token automatically

## Quick Start

Create the server:

```bash
alphagsm myqwserver create qwserver
```

Run setup:

```bash
alphagsm myqwserver setup
```

Start it:

```bash
alphagsm myqwserver start
```

Check it:

```bash
alphagsm myqwserver status
```

Stop it:

```bash
alphagsm myqwserver stop
```

## Setup Details

Setup configures:

- the game port (default 27500)
- the install directory
- downloads the MVDSV server archive
- stages the public nQuake shareware data, KTX runtime/configs, and the core public QuakeWorld maps required for anonymous startup

## Useful Commands

```bash
alphagsm myqwserver update
alphagsm myqwserver backup
```

## Notes

- Module name: `qwserver`
- Default port: 27500

## Developer Notes

### Run File

- **Executable**: `mvdsv`
- **Location**: `<install_dir>/mvdsv`
- **Engine**: QuakeWorld / MVDSV
- **Launch mode**: `-mem 64 -game ktx`

### Server Configuration

- **Config file**: `<install_dir>/ktx/server.cfg`
- **Template**: See [server-templates/qwserver/](../server-templates/qwserver/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/qw/maps/`
- **KTX runtime**: `<install_dir>/ktx/`
- **Mod directory**: `<install_dir>/qw/`
- **Workshop support**: No

### Query And Info

- `alphagsm myqwserver query` uses the real QuakeWorld `status` UDP probe on the main game port
- `alphagsm myqwserver info --json` reports protocol `quakeworld`

## Mod Sources

QuakeWorld supports AlphaGSM-managed direct `url` mod sources for content-only `.pak` payloads.

Supported payload shapes:

- a direct `.pak` URL
- an archive containing bare `.pak` files at the archive root
- an archive containing `qw/<name>.pak`

AlphaGSM installs approved `.pak` content into `qw/`, tracks only the files it owns, and keeps that content directory in the managed backup targets.

Examples:

```bash
alphagsm myqwserver mod add url https://example.com/pak1.pak
alphagsm myqwserver mod add url https://example.com/custom-content.zip
alphagsm myqwserver mod apply
alphagsm myqwserver mod cleanup
```
