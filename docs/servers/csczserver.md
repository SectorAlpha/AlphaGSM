# Counter-Strike: Condition Zero

This guide covers the `csczserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycsczserv create csczserver
```

Run setup:

```bash
alphagsm mycsczserv setup
```

Start it:

```bash
alphagsm mycsczserv start
```

Check it:

```bash
alphagsm mycsczserv status
```

Stop it:

```bash
alphagsm mycsczserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm mycsczserv update
alphagsm mycsczserv backup
```

## Notes

- Module name: `csczserver`
- Default port: 27015
