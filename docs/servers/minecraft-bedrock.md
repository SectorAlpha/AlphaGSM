# Minecraft Bedrock Edition

This guide covers the `minecraft.bedrock` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybedrock create minecraft.bedrock
```

Run setup:

```bash
alphagsm mybedrock setup
```

Start it:

```bash
alphagsm mybedrock start
```

Check it:

```bash
alphagsm mybedrock status
```

Stop it:

```bash
alphagsm mybedrock stop
```

## Setup Details

Setup configures:

- the game port (default 19132)
- the install directory

## Useful Commands

```bash
alphagsm mybedrock update
alphagsm mybedrock backup
```

## Notes

- Module name: `minecraft.bedrock`
- Default port: 19132
