# Counter-Strike: Global Offensive

This is the legacy CS:GO guide for `counterstrikeglobaloffensive`.
Use [`counterstrike2`](counterstrike2.md) for the current CS2 dedicated-server flow.

`counterstrikeglobaloffensive` is currently `DISABLED` in the checked-in
support tracker. On the documented Ubuntu 24.04 Linux baseline, SteamCMD app
`740` installs legacy CS:GO build `1575`; the server reaches Steam, receives
`MasterRequestRestart`, and shuts itself down while hibernating.

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

<!-- alphagsm-server-variables:start -->

## Server variables

After `create counterstrikeglobaloffensive`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `de_dust2`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM CS:GO Server`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->
