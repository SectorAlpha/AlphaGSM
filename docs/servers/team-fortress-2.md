# Team Fortress 2

This guide is for running a Team Fortress 2 server with AlphaGSM.

## What You Need

- `screen`
- SteamCMD runtime libraries:
  - `lib32gcc-s1`
  - `lib32stdc++6`
- the Python packages in `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytf2 create teamfortress2
```

Run setup:

```bash
alphagsm mytf2 setup
```

Start it:

```bash
alphagsm mytf2 start
```

Check it:

```bash
alphagsm mytf2 status
```

Stop it:

```bash
alphagsm mytf2 stop
```

## Useful Commands

```bash
alphagsm mytf2 update
alphagsm mytf2 update -r
```

## Best Working Example

The best full example in the repository is:

- `smoke_tests/run_tf2.sh`

It uses this command flow:

```bash
alphagsm ittf2 create teamfortress2
alphagsm ittf2 setup -n PORT /tmp/tf2-server
alphagsm ittf2 start
alphagsm ittf2 status
alphagsm ittf2 stop
alphagsm ittf2 status
```

## Notes

- `tf2` is the short name people usually type.
- setup can take a while because TF2 installs through SteamCMD.
- if you want the most realistic example, follow the smoke test.
