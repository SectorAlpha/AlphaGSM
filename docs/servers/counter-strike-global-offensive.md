# Counter-Strike: Global Offensive

This is the legacy CS:GO guide for `counterstrikeglobaloffensive`.
Use [`counterstrike2`](counterstrike2.md) for the current CS2 dedicated-server flow.

## Requirements

- `screen`
- SteamCMD runtime libraries:
  - `lib32gcc-s1`
  - `lib32stdc++6`
- Python dependencies from `requirements.txt`

## Create and Set Up

```bash
alphagsm mycsgo create csgo
alphagsm mycsgo setup
```

The setup flow configures:

- the game port
- the install directory
- the executable name
- default configuration and backup settings

## Common Commands

```bash
alphagsm mycsgo start
alphagsm mycsgo status
alphagsm mycsgo update
alphagsm mycsgo update -v -r
alphagsm mycsgo stop
```

## Notes

- Like TF2, CS:GO is managed through SteamCMD.
- The module shares the same general Steam game lifecycle as TF2: setup, start, stop, status, update, and restart.
- Backup support is configured during setup through the shared backup helpers in `utils.backups`.
- This legacy module is disabled in automated testing.
