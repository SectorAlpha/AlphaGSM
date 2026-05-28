# Saleblazers

This guide covers the `saleblazersserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysaleblaz create saleblazersserver
```

Run setup:

```bash
alphagsm mysaleblaz setup
```

Start it:

```bash
alphagsm mysaleblaz start
```

Check it:

```bash
alphagsm mysaleblaz status
```

Stop it:

```bash
alphagsm mysaleblaz stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the query port (default 27016)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mysaleblaz update
alphagsm mysaleblaz backup
```

## Notes

- Module name: `saleblazersserver`
- Default game port: 27015
- Default query port: 27016
- Current validation status: still not enabled on Linux/Wine as of 2026-05-28. The headless wrapper now gets the dedicated server through `Launching server...`, `Waiting for Hosting Selections...`, and `Connected to Console Window!`, but the process still exits before A2S readiness with Null graphics / localization errors in `server.log`.

## Developer Notes

### Run File

- **Executable**: `Default/Saleblazers.exe`
- **Location**: `<install_dir>/Default/Saleblazers.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `3099600`

AlphaGSM launches the server with
`-headless -batchmode -nographics -logFile ./server.log` and treats
`info --json` returning protocol `a2s` as the readiness gate. The plain Unity
startup text in `server.log` is not stable enough to use as the only readiness
marker. On Linux hosts AlphaGSM now prefers `xvfb-run` with SDL `x11` video
and dummy audio so the dedicated process gets past the earlier headless
window-creation failure while also matching the upstream Saleblazers headless
server mode more closely.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/saleblazersserver/](../server-templates/saleblazersserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
