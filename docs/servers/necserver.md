# Necesse

This guide covers the `necserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynecserve create necserver
```

Run setup:

```bash
alphagsm mynecserve setup
```

Start it:

```bash
alphagsm mynecserve start
```

Check it:

```bash
alphagsm mynecserve status
```

Stop it:

```bash
alphagsm mynecserve stop
```

## Setup Details

Setup configures:

- the game port (default 14159)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mynecserve update
alphagsm mynecserve backup
```

## Notes

- Module name: `necserver`
- Default port: 14159
