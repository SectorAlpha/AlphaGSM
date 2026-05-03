# Unreal Tournament 99

This guide covers the `ut99server` module in AlphaGSM.

## Requirements

- `screen`
- `7z` or `7zz` (`p7zip-full` on Debian/Ubuntu)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myut99serv create ut99server
```

Run setup:

```bash
alphagsm myut99serv setup
```

Start it:

```bash
alphagsm myut99serv start
```

Check it:

```bash
alphagsm myut99serv status
```

Stop it:

```bash
alphagsm myut99serv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and runs the OldUnreal Linux installer
- accepts the Epic Games Terms of Service non-interactively for automated setup

## Useful Commands

```bash
alphagsm myut99serv update
alphagsm myut99serv backup
```

## Mod Sources

Unreal Tournament 99 content management currently targets the canonical custom
content directories under the server root:

- `Maps/`
- `Music/`
- `Sounds/`
- `Textures/`

Current mod source support is direct `url` entries only.

- `mod add url <https-url>` accepts supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload unpacks into the approved UT99 content directories above.
- `mod add url <https-url>` also accepts direct content-file URLs such as `.unr`, `.utx`, `.uax`, and `.umx`; AlphaGSM places each file into the matching canonical content directory automatically.
- `mod cleanup` removes only AlphaGSM-tracked files and keeps its cache/state under `.alphagsm/mods/ut99server/`.
- The first UT99 content slice intentionally excludes `System/` payloads, code packages, and mutators; archives that require those paths are rejected instead of being partially installed.

Examples:

```bash
alphagsm myut99serv mod add url https://example.invalid/mappack.zip
alphagsm myut99serv mod add url https://example.invalid/DM-Deck-Test.unr
alphagsm myut99serv mod apply
alphagsm myut99serv mod cleanup
```

## Notes

- Module name: `ut99server`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: architecture-specific OldUnreal launcher
- **Typical amd64 location**: `<install_dir>/System64/ucc-bin-amd64`
- **Compatibility wrapper**: `<install_dir>/System64/ucc-bin` when present
- **Engine**: Custom

### Server Configuration

- **Config file**: typically `System64/UnrealTournament.ini` on modern Linux installs
- **Max players**: `16`
- **Template**: See [server-templates/ut99server/](../server-templates/ut99server/) if available

### Query and Info

- `alphagsm <server> query` and `alphagsm <server> info` currently use generic UDP reachability
- the screen log at `alphagsm-home/logs/` is the best readiness signal for startup diagnostics

### Maps and Mods

- **Map directory**: `Maps/`
- **Mod directory**: `Maps/`, `Music/`, `Sounds/`, `Textures/`
- **Mod notes**: AlphaGSM can now track direct archive and direct content-file `url` entries for UT99, install only approved custom-content payloads, and clean up only AlphaGSM-managed files from `.alphagsm/mods/ut99server/`. The initial UT99 content surface rejects `System/` payloads on purpose.
- **Workshop support**: No
