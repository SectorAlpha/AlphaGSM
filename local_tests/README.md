# Local Steam auth and BYO tests

This directory is the local-only suite for servers that need a Steam login or
owned files. `make test`, `pytest tests`, and GitHub Actions do not collect it.

Run it with:

```bash
scripts/run_local_auth_tests.sh unit
scripts/run_local_auth_tests.sh integration --suite byo --server q3server --profile owned
scripts/run_local_auth_tests.sh integration --suite auth --server acserver --profile owned
scripts/run_local_auth_tests.sh integration --server codserver --assets /path/to/owned-files
```

`unit` checks that every ENABLED (AUTH) and ENABLED (BYO) module imports, that
declared provider metadata matches `enabled_auth_servers.conf`, and that file
and export BYO modules have a `byo_assets.json` recipe. It does not log in and
does not download.

`integration` runs AlphaGSM `create`, `setup`, `start`, `query`, `info`,
`info --json`, and `stop` for the servers you name. Pick `--profile NAME` or
`--assets PATH`. Those two sources are mutually exclusive. `--server all`
also requires `--confirm-all`.

Create the profile from a terminal before using it:

```bash
alphagsm steam-auth login owned YOUR_STEAM_USERNAME
alphagsm steam-auth status owned
```

SteamCMD asks for the password and Steam Guard in that terminal. The script
rejects `--password`, `--token`, and `--guard`. It records only the profile
name. The profile directory stays in the AlphaGSM state directory, normally
`~/.alphagsm/steam-auth/NAME/`. Pass `--state-dir` when the profile lives
somewhere else. That directory must be a Linux filesystem that stores Unix
owners and modes.

Disposable servers go under `.local-tests/local-auth/` unless you pass
`--work-dir`. That path is gitignored. Do not point it at the git checkout.

The same login is used when AlphaGSM itself is the host process and game
servers use Docker. Set `ALPHAGSM_LOCAL_RUNTIME=docker` for that integration
run. The profile is not mounted into the game container.

When AlphaGSM is the manager container, open a terminal with
`./alphagsm-docker shell` and run `python alphagsm steam-auth login owned YOUR_STEAM_USERNAME`
there. Forwarded `./alphagsm-docker` commands currently disable the terminal,
so the login has to happen in that shell. Later setup commands can use
`./alphagsm-docker`. Keep the profile on the manager state directory, which is
bind-mounted at the same absolute path, and keep server installs beside it
rather than inside `steam-auth/`.

A standalone `alphagsm` binary can run the same integration flow when
`ALPHAGSM_BINARY` points at that executable.
