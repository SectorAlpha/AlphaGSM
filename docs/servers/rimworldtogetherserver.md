# RimWorld Together

This guide covers the `rimworldtogetherserver` module in AlphaGSM.

`rimworldtogetherserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrimworld create rimworldtogetherserver
```

Run setup:

```bash
alphagsm myrimworld setup
```

Start it:

```bash
alphagsm myrimworld start
```

Check it:

```bash
alphagsm myrimworld status
```

Stop it:

```bash
alphagsm myrimworld stop
```

## Setup Details

Setup configures:

- the game port (default 25555)
- the install directory
- downloads and extracts the server archive

## Structured Settings

Only the game port is schema-backed for this module:

```bash
alphagsm myrimworld set port 25555
```

The module also accepts `gameport` as an alias for `port`.

## Useful Commands

```bash
alphagsm myrimworld update
alphagsm myrimworld backup
```

## Notes

- Module name: `rimworldtogetherserver`
- Default port: 25555

<!-- alphagsm-server-variables:start -->

## Server variables

After `create rimworldtogetherserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `port` | gameport | integer | The game port used by the RimWorld Together server. Example: `25555`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `GameServer`
- **Location**: `<install_dir>/GameServer`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/rimworldtogetherserver/](../server-templates/rimworldtogetherserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
