# DayZ Arma 2 Epoch

This guide covers the `dayzarma2epochserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydayzarma create dayzarma2epochserver
```

Run setup:

```bash
alphagsm mydayzarma setup
```

Start it:

```bash
alphagsm mydayzarma start
```

Check it:

```bash
alphagsm mydayzarma status
```

Stop it:

```bash
alphagsm mydayzarma stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydayzarma update
alphagsm mydayzarma backup
```

## Notes

- Module name: `dayzarma2epochserver`
- Default port: 2302
