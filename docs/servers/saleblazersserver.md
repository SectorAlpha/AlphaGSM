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
- Current validation status: still not enabled on Linux/Wine as of 2026-05-28. A fresh host smoke under `/media/cosmosquark/a55b079e-515f-4798-a120-b1e69dda0b22/useme` completed SteamCMD setup, but AlphaGSM never reached A2S readiness on the configured `port=35093` / `queryport=27016`: `info --json` returned no payload for 180 seconds, direct probes failed with `A2S query failed: timed out`, and no listener appeared on either port. The checked-in `-headless -batchmode -nographics -logFile` launcher still stalls after the Unity localization `OperationException` on a `Null` graphics device. A manual `xvfb-run` + SDL `x11` + dummy audio + software-GL launch without `-headless` advanced one step further to `Starting server console window process...` and `Connected to Console Window!`, which makes that non-headless Linux launcher shape the next bounded fix to validate in-module before re-enabling.

## Developer Notes

### Run File

- **Executable**: `Default/Saleblazers.exe`
- **Location**: `<install_dir>/Default/Saleblazers.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `3099600`

AlphaGSM currently launches the server with
`-headless -batchmode -nographics -logFile ./server.log` and treats
`info --json` returning protocol `a2s` as the readiness gate. The plain Unity
startup text in `server.log` is not stable enough to use as the only readiness
marker. On Linux hosts AlphaGSM now prefers `xvfb-run` with SDL `x11` video
and dummy audio so the dedicated process gets past the earlier headless
window-creation failure while also matching the upstream Saleblazers headless
server mode more closely, but fresh validation shows that this launcher shape
still never binds the configured game/query ports before A2S times out. The
best current fallback experiment is the same `xvfb-run` wrapper plus software
GL (`LIBGL_ALWAYS_SOFTWARE=1`) without `-headless`, because that was the only
observed variant that reached `Connected to Console Window!` in a fresh
scratch-run reproduction.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/saleblazersserver/](../server-templates/saleblazersserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
