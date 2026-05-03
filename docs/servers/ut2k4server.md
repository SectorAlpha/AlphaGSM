# Unreal Tournament 2004

This guide covers the `ut2k4server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myut2k4ser create ut2k4server
```

Run setup:

```bash
alphagsm myut2k4ser setup
```

Start it:

```bash
alphagsm myut2k4ser start
```

Check it:

```bash
alphagsm myut2k4ser status
```

Stop it:

```bash
alphagsm myut2k4ser stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myut2k4ser update
alphagsm myut2k4ser backup
```

## Mod Sources

Unreal Tournament 2004 content management currently targets the canonical
custom-content directories under the server root:

- `Animations/`
- `KarmaData/`
- `Maps/`
- `Music/`
- `Sounds/`
- `StaticMeshes/`
- `Textures/`

Current mod source support is direct `url` entries only.

- `mod add url <https-url>` accepts supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload unpacks into the approved UT2004 content directories above.
- `mod add url <https-url>` also accepts direct content-file URLs such as `.ut2`, `.utx`, `.uax`, `.ukx`, `.usx`, `.ogg`, and `.ka`; AlphaGSM places each file into the matching canonical content directory automatically.
- `mod cleanup` removes only AlphaGSM-tracked files and keeps its cache/state under `.alphagsm/mods/ut2k4server/`.
- The first UT2004 content slice intentionally excludes `System/` payloads, mutators, and code packages; archives that require those paths are rejected instead of being partially installed.

Examples:

```bash
alphagsm myut2k4ser mod add url https://example.invalid/mappack.zip
alphagsm myut2k4ser mod add url https://example.invalid/DM-Rankin-FE.ut2
alphagsm myut2k4ser mod apply
alphagsm myut2k4ser mod cleanup
```

## Notes

- Module name: `ut2k4server`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `System/ucc-bin`
- **Location**: `<install_dir>/System/ucc-bin`
- **Engine**: Custom

### Server Configuration

- **Config file**: `System/UT2004.ini`
- **Max players**: `16`
- **Template**: See [server-templates/ut2k4server/](../server-templates/ut2k4server/) if available

### Maps and Mods

- **Map directory**: `Maps/`
- **Mod directory**: `Animations/`, `KarmaData/`, `Maps/`, `Music/`, `Sounds/`, `StaticMeshes/`, `Textures/`
- **Mod notes**: AlphaGSM can now track direct archive and direct content-file `url` entries for UT2004, install only approved custom-content payloads, and clean up only AlphaGSM-managed files from `.alphagsm/mods/ut2k4server/`. The initial UT2004 content surface rejects `System/` payloads on purpose.
- **Workshop support**: No
