# Call of Duty: Modern Warfare 3

This guide covers the `mw3server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymw3serve create mw3server
```

Run setup:

```bash
alphagsm mymw3serve setup
```

Start it:

```bash
alphagsm mymw3serve start
```

Check it:

```bash
alphagsm mymw3serve status
```

Stop it:

```bash
alphagsm mymw3serve stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymw3serve update
alphagsm mymw3serve backup
```

## Notes

- Module name: `mw3server`
- Default port: 27016
