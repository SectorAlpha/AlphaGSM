# Life is Feudal: Your Own

This guide covers the `lifeisfeudalserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylifeisfe create lifeisfeudalserver
```

Run setup:

```bash
alphagsm mylifeisfe setup
```

Start it:

```bash
alphagsm mylifeisfe start
```

Check it:

```bash
alphagsm mylifeisfe status
```

Stop it:

```bash
alphagsm mylifeisfe stop
```

## Setup Details

Setup configures:

- the game port (default 28001)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylifeisfe update
alphagsm mylifeisfe backup
```

## Notes

- Module name: `lifeisfeudalserver`
- Default port: 28001
