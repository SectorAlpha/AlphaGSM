# Mount & Blade: Warband

This guide covers the `warbandserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts (the official TaleWorlds archive is Windows-only)
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
- downloads and extracts the official `mb_warband_dedicated_1174.zip` archive
- syncs `Sample_Battle.txt` so `set_port`, `set_steam_port`, and `set_max_players` match the configured AlphaGSM server settings

## Useful Commands

```bash
alphagsm mywarbands update
alphagsm mywarbands backup
```

## Notes

- Module name: `warbandserver`
- Default port: 7240
- AlphaGSM uses the direct TaleWorlds archive URL because the public Warband page is now fronted by a Cloudflare challenge that blocks automated version scraping.
- The official `1.174` dedicated archive installs `Mount&Blade Warband Dedicated/mb_warband_dedicated.exe`, so Linux hosts run it through Wine or Proton-GE.
- Headless Linux runs use `xvfb-run` when it is available so Wine can create the minimal virtual display Warband expects at startup.
- Smoke and integration readiness now wait on `info --json` reporting protocol `tcp`, because the dedicated server does not emit reliable startup markers into the outer screen log and AlphaGSM currently observes Warband through generic TCP reachability.

## Developer Notes

### Run File

- **Executable**: `mb_warband_dedicated.exe`
- **Location**: `<install_dir>/Mount&Blade Warband Dedicated/mb_warband_dedicated.exe`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<install_dir>/Mount&Blade Warband Dedicated/Sample_Battle.txt`
- **Max players**: `64`
- **Template**: See [server-templates/warbandserver/](../server-templates/warbandserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
