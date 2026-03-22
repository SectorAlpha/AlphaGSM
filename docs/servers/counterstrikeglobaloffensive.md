# CS:GO-specific

This guide covers the `counterstrikeglobaloffensive` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycounters create counterstrikeglobaloffensive
```

Run setup:

```bash
alphagsm mycounters setup
```

Start it:

```bash
alphagsm mycounters start
```

Check it:

```bash
alphagsm mycounters status
```

Stop it:

```bash
alphagsm mycounters stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycounters update
alphagsm mycounters backup
```

## Notes

- Module name: `counterstrikeglobaloffensive`
- Default port: 27015
