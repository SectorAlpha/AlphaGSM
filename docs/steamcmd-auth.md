# SteamCMD Auth Profiles

**Status: not implemented.** This page is a public TODO so AUTH-gated Steam
servers are not mistaken for missing features or for BYO asset requirements.

## Why this exists

Many dedicated servers install with SteamCMD `login anonymous`. Some do not.
Those modules are marked **ENABLED (AUTH)** in
[TEST_STATUS.md](TEST_STATUS.md): AlphaGSM knows how to run them, but GitHub
Actions has no entitled Steam account, so setup cannot download the files.

Today there is no `alphagsm steam-auth …` command. If a server needs a Steam
login, you must run SteamCMD yourself or wait for this work.

## Planned operator flow

A future AlphaGSM-managed **global** SteamCMD profile, not a password in each
server's JSON:

```bash
alphagsm steam-auth add default
alphagsm steam-auth login default
alphagsm steam-auth status default
alphagsm steam-auth logout default
```

Intended behaviour:

- Prompt for username / password / Steam Guard only during login.
- Let SteamCMD persist its own session under an AlphaGSM directory such as
  `~/.alphagsm/steam-auth/default/`.
- Reuse that session for later `setup` and `update` without storing the
  password in the per-server datastore.
- Mount the same session into Docker installs. Images stay generic.

A Steam account should be dedicated to server management. Valve still only
allows one login location at a time.

Game-level tokens (TF2 GSLT, license keys) are a separate secret path, not a
substitute for SteamCMD login.

## What this is not

- Not **ENABLED (BYO)**. BYO means you supply game files, maps, or a URL.
  AUTH means a provider login or token.
- Not implemented in the current CLI. Do not expect `steam-auth` to exist yet.
- Not a reason to disable a module that otherwise works once files are present.

## Related

- [Everyday Commands](commands.md) — current CLI
- [Updating Servers And AlphaGSM](updating.md) — SteamCMD `update` for
  anonymous installs
- [Adding A Game Server](adding-a-game-server.md) — declare
  `get_provider_requirements` as `provider-auth` when a module needs this
