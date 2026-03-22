# Call of Duty: Black Ops III

This guide covers the `blackops3server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myblackops create blackops3server
```

Run setup:

```bash
alphagsm myblackops setup
```

Start it:

```bash
alphagsm myblackops start
```

Check it:

```bash
alphagsm myblackops status
```

Stop it:

```bash
alphagsm myblackops stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myblackops update
alphagsm myblackops backup
```

## Notes

- Module name: `blackops3server`
- Default port: 27015
