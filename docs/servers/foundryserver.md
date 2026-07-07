# FOUNDRY

This guide covers the `foundryserver` module in AlphaGSM.

`foundryserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that staged-server prerequisite,
while local runs remain process-backed by default unless you opt into the
Docker backend.

## Requirements

- `screen`
- a native FOUNDRY dedicated server tree containing `FoundryDedicatedServer`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfoundrys create foundryserver
```

Run setup:

```bash
alphagsm myfoundrys setup
```

`foundryserver` is supported in `ENABLED (BYO)` mode. The current anonymous
SteamCMD app does not deliver the required native server payload, so before
`setup` or `start` you should stage a native FOUNDRY dedicated server tree
containing `FoundryDedicatedServer` inside your chosen `<install_dir>/`.

Start it:

```bash
alphagsm myfoundrys start
```

Check it:

```bash
alphagsm myfoundrys status
```

Stop it:

```bash
alphagsm myfoundrys stop
```

## Setup Details

Setup configures:

- the game port (default 37200)
- the install directory

Suggested flow:

```bash
alphagsm myfoundrys create foundryserver
alphagsm myfoundrys setup -n 37200 /path/to/foundry
# copy FoundryDedicatedServer and the rest of the native server tree into /path/to/foundry/
alphagsm myfoundrys start
```

## Useful Commands

```bash
alphagsm myfoundrys update
alphagsm myfoundrys backup
```

## Notes

- Module name: `foundryserver`
- Default port: 37200

## Developer Notes

### Run File

- **Executable**: `FoundryDedicatedServer`
- **Location**: `<install_dir>/FoundryDedicatedServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2915550`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/foundryserver/](../server-templates/foundryserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
