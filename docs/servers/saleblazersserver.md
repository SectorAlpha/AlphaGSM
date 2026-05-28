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
- Current validation status: still not enabled on Linux/Wine as of 2026-05-29. The module now promotes the best-known Linux launcher shape into code: `xvfb-run` plus SDL `x11`, dummy audio, software GL (`LIBGL_ALWAYS_SOFTWARE=1`), and no explicit `-headless` flag. A fresh bounded repro against an already-installed tree under `/media/cosmosquark/a55b079e-515f-4798-a120-b1e69dda0b22/useme/saleblazers-runtime-debug/` confirmed the newer upstream `-config` flow is real: the main game log reaches `Launching server...`, `Config file found! Loading config from PATH ./DedicatedServerConfig.json`, and `Starting server console window process...`, while the generated Proton `LocalLow/.../ServerConsoleLogs/ServerConsole_*.log` reaches the dedicated-server banner and `Waiting for Main Game Connection...`. The remaining blocker is now precise: even with a valid config file and the current Xvfb wrapper, the Linux/Wine run still advertises `Port 55000` in the early multicast line instead of the configured hosting port, the main game never progresses to `Server hosted on port ...` or `Connected to Console Window!`, and AlphaGSM still cannot prove `query` / `info` / `info --json` readiness on A2S.

## Developer Notes

### Run File

- **Executable**: `Default/Saleblazers.exe`
- **Location**: `<install_dir>/Default/Saleblazers.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `3099600`

AlphaGSM treats `info --json` returning protocol `a2s` as the readiness gate.
The plain Unity startup text in `server.log` is not stable enough to use as
the only readiness marker. On Linux hosts AlphaGSM now launches Saleblazers
through `xvfb-run` with SDL `x11` video, dummy audio, software GL
(`LIBGL_ALWAYS_SOFTWARE=1`), and without the explicit `-headless` flag because
that is the first launcher shape that consistently reaches the dedicated-server
bring-up path under Wine/Proton. The upstream docs also document
`-config <DedicatedServerConfig.json>` as the supported non-interactive launch
surface, and fresh repros confirm the game does load that file on Linux/Wine.
The blocker is deeper: after `Config file found! ...` the main game stops at
`Starting server console window process...`, while the generated
`ServerConsoleLogs/ServerConsole_*.log` waits for the main game connection and
never reaches the later `Server hosted on port ...` / Steam-init path.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/saleblazersserver/](../server-templates/saleblazersserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
