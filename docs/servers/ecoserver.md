# Eco

This guide covers the `ecoserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myecoserve create ecoserver
```

Run setup:

```bash
alphagsm myecoserve setup
```

Start it:

```bash
alphagsm myecoserve start
```

Check it:

```bash
alphagsm myecoserve status
```

Stop it:

```bash
alphagsm myecoserve stop
```

## Setup Details

Setup configures:

- the game port (default 3000)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myecoserve update
alphagsm myecoserve backup
```

## Notes

- Module name: `ecoserver`
- Default port: 3000
