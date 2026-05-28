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
- Current validation status: still not enabled on Linux/Wine as of 2026-05-28. The module now promotes the best-known Linux launcher shape into code: `xvfb-run` plus SDL `x11`, dummy audio, software GL (`LIBGL_ALWAYS_SOFTWARE=1`), and no explicit `-headless` flag. A bounded direct repro against an already-installed tree under `/media/cosmosquark/a55b079e-515f-4798-a120-b1e69dda0b22/useme/saleblazers-runtime-debug/` reached `Launching server...`, `Starting server console window process...`, `Waiting for Hosting Selections...`, and `Connected to Console Window!`, which is better than the older `Failed to create batch mode window` / immediate NullGfx stall. The blocker is now narrower but still real: during that live repro, `ss -lpun` showed no listener on either the stored game port (`55000`) or the default query port (`27016`), so AlphaGSM still cannot prove `query` / `info` / `info --json` readiness.

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
that is the first launcher shape that consistently reaches `Connected to
Console Window!` in local reproductions. Even with that improvement, fresh
validation still has not shown a live listener on the managed game/query ports,
so the remaining work is deeper than the wrapper flags alone.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/saleblazersserver/](../server-templates/saleblazersserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
