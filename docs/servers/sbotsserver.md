# StickyBots

This guide covers the `sbotsserver` module in AlphaGSM.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD dependencies from the normal AlphaGSM install path

## Quick Start

```bash
alphagsm mysbots create sbotsserver
alphagsm mysbots setup
alphagsm mysbots start
alphagsm mysbots status
alphagsm mysbots stop
```

## Notes

- Module name: `sbotsserver`
- LinuxGSM short alias: `sbots`
- Steam app id: `974130`
- Default port: `7777`
- Default query port: `27015`
- Query/info protocol: `a2s`

## Developer Notes

- AlphaGSM installs the Linux dedicated payload through SteamCMD anonymous login.
- The upstream install ships a launcher script at `blank1Server.sh` that wraps `blank1/Binaries/Linux/blank1Server-Linux-Shipping`.
- Headless Linux starts currently print `SteamAPI_Init()` warnings, but the dedicated server still reaches a working A2S query state on `queryport`; AlphaGSM smoke and integration coverage should treat `info --json` protocol `a2s` as the readiness gate instead of waiting for a startup log.