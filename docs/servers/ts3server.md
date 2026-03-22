# TeamSpeak 3

This guide covers the `ts3server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myts3serve create ts3server
```

Run setup:

```bash
alphagsm myts3serve setup
```

Start it:

```bash
alphagsm myts3serve start
```

Check it:

```bash
alphagsm myts3serve status
```

Stop it:

```bash
alphagsm myts3serve stop
```

## Setup Details

Setup configures:

- the game port (default 10011)
- the install directory

## Useful Commands

```bash
alphagsm myts3serve update
alphagsm myts3serve backup
```

## Notes

- Module name: `ts3server`
- Default port: 10011
