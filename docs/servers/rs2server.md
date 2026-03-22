# Rising Storm 2: Vietnam

This guide covers the `rs2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrs2serve create rs2server
```

Run setup:

```bash
alphagsm myrs2serve setup
```

Start it:

```bash
alphagsm myrs2serve start
```

Check it:

```bash
alphagsm myrs2serve status
```

Stop it:

```bash
alphagsm myrs2serve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myrs2serve update
alphagsm myrs2serve backup
```

## Notes

- Module name: `rs2server`
- Default port: 27015
