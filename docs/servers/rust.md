# Rust

This guide covers the `rust` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrust create rust
```

Run setup:

```bash
alphagsm myrust setup
```

Start it:

```bash
alphagsm myrust start
```

Check it:

```bash
alphagsm myrust status
```

Stop it:

```bash
alphagsm myrust stop
```

## Setup Details

Setup configures:

- the game port (default 28016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myrust update
alphagsm myrust backup
```

## Notes

- Module name: `rust`
- Default port: 28016
