# Warfork

This guide covers the `wfserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywfserver create wfserver
```

Run setup:

```bash
alphagsm mywfserver setup
```

Start it:

```bash
alphagsm mywfserver start
```

Check it:

```bash
alphagsm mywfserver status
```

Stop it:

```bash
alphagsm mywfserver stop
```

## Setup Details

Setup configures:

- the game port (default 44400)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mywfserver update
alphagsm mywfserver backup
```

## Notes

- Module name: `wfserver`
- Default port: 44400
