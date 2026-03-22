# Wreckfest

This guide covers the `wreckfestserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywreckfes create wreckfestserver
```

Run setup:

```bash
alphagsm mywreckfes setup
```

Start it:

```bash
alphagsm mywreckfes start
```

Check it:

```bash
alphagsm mywreckfes status
```

Stop it:

```bash
alphagsm mywreckfes stop
```

## Setup Details

Setup configures:

- the game port (default 33540)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mywreckfes update
alphagsm mywreckfes backup
```

## Notes

- Module name: `wreckfestserver`
- Default port: 33540
