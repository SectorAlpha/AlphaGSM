# Saleblazers

This guide covers the `saleblazersserver` module in AlphaGSM.

`saleblazersserver` is being revalidated on the documented Ubuntu 24.04 Linux
baseline. Docker is the required runtime path, and GitHub CI additionally
exercises the process path where it remains viable. The previous 2026-05-29
process validation predates the current Docker display-runtime correction, so
Docker lifecycle support must not be treated as freshly passed until the current
GitHub Actions run is green.

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
- the derived helper port (`port + 1`, default 27016)
- the install directory
- SteamCMD downloads the Windows dedicated server files
- AlphaGSM syncs the managed `port`, lobby name, password, and player cap into
  `DedicatedServerConfig.json`

## Useful Commands

```bash
alphagsm mysaleblaz update
alphagsm mysaleblaz backup
```

## Notes

- Module name: `saleblazersserver`
- Default game port: 27015
- Default helper port: 27016 (`port + 1`)
- Current validation status: pending the current GitHub Actions rerun. AlphaGSM starts the upstream executable from `<install_dir>/Default`, passes the managed root config as `-config ../DedicatedServerConfig.json`, runs it under `xvfb-run` plus SDL `x11`, dummy audio, and software GL, and treats the live helper surface as generic `udp` on `port + 1`. The current readiness markers are `Server hosted on port ...` and `Connected to Console Window!`, and `query`, `info`, and `info --json` must all pass on the derived helper port.

## Developer Notes

### Run File

- **Executable**: `Default/Saleblazers.exe`
- **Location**: `<install_dir>/Default/Saleblazers.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `3099600`

AlphaGSM now treats `info --json` returning protocol `udp` on the derived
helper port (`port + 1`) as the readiness gate. The plain Unity startup text in
`server.log` is not stable enough to use as the only readiness marker, so the
checked-in smoke and integration flows wait for the later
`Server hosted on port ...` / `Connected to Console Window!` lines before
confirming the helper listener. On Linux hosts AlphaGSM launches Saleblazers
through `xvfb-run` with SDL `x11` video, dummy audio, software GL
(`LIBGL_ALWAYS_SOFTWARE=1`), and the game's `-headless` option to load the
configured lobby unattended, without Unity's `-batchmode` or `-nographics`
flags. The batch-mode window path fails before the
dedicated listener is created under Wine/Proton. AlphaGSM always starts from
the upstream-required `Default` executable directory and passes the root-owned
config as `-config ../DedicatedServerConfig.json`, so process and Docker
runtimes consume the same module launch contract. Docker explicitly enables
the Wine/Proton runtime image's matching 24-bit Xvfb display. AlphaGSM keeps
the generated config aligned with the owned game port plus the basic lobby
settings exposed through `set`.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/saleblazersserver/](../server-templates/saleblazersserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
