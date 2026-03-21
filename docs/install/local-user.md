# Local User Install

This install path is for one Linux user running AlphaGSM for their own account.

## What It Does

The local install script:

- copies AlphaGSM into your home directory
- makes a config file for you
- creates a command link in `~/.local/bin`

## Run It

From the repository root:

```bash
bash ./scripts/install-local-user.sh
```

## Default Paths

- code: `~/.local/lib/alphagsm`
- command: `~/.local/bin/alphagsm`
- config: `~/.local/lib/alphagsm/alphagsm.conf`

## After Install

If `~/.local/bin` is not already in your `PATH`, add it in your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then you can run:

```bash
alphagsm --help
```
