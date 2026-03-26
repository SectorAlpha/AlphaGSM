# Mount & Blade: Warband

This guide covers the `warbandserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywarbands create warbandserver
```

Run setup:

```bash
alphagsm mywarbands setup
```

Start it:

```bash
alphagsm mywarbands start
```

Check it:

```bash
alphagsm mywarbands status
```

Stop it:

```bash
alphagsm mywarbands stop
```

## Setup Details

Setup configures:

- the game port (default 7240)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mywarbands update
alphagsm mywarbands backup
```

## Notes

- Module name: `warbandserver`
- Default port: 7240

## Developer Notes

### Run File

- **Executable**: `mb_warband_dedicated`
- **Location**: `<install_dir>/mb_warband_dedicated`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Max players**: `64`
- **Template**: See [server-templates/warbandserver/](../server-templates/warbandserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
