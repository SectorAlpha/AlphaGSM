# Auth-first BYO setup and Steam-library import

The user prefers AlphaGSM to authenticate and download owned files itself, with an explicit installed-Steam-directory alternative. The user selected remembering the profile name per server. This extends the approved local validation campaign; credential handling stays in the existing private profile API.

## Commands and selection

Preferred: `alphagsm steam-auth login owned USERNAME`, then `alphagsm TAG setup -n PORT DIR --auth-profile owned`. Setup remembers only `steam_auth_profile: owned` after successful acquisition or a valid existing file check. Later setup uses the remembered profile when required BYO files are missing. Existing valid assets avoid redundant full-app downloads; forced acquisition remains `assets fetch steam-owned --auth-profile owned`.

Alternative: `setup ... --steam-dir /path/to/Steam` (or a SteamLibrary root / explicit steamapps directory). Resolve the recipe's single declared Steam source AppID from public local library/app manifests, then pass only that app directory through the existing allowlist importer. An explicit Steam directory or existing `--assets PATH` overrides remembered auth for that invocation. Explicit auth-profile, steam-dir and assets selectors are mutually exclusive. Auth failures never silently fall back to anonymous, installed Steam files or an unrelated source.

Only managed recipes with exactly one declared SteamCMD source support these new acquisition options. Other BYO recipes retain their exports/manual staging requirements; do not infer app IDs for the remaining games. Existing unrelated server setup remains unchanged. Setup without a source selector or remembered profile retains its engine-only/manual preparation behavior; only an explicit or remembered profile triggers authenticated acquisition. With missing files and no profile, recommend the authenticated setup form before mentioning local alternatives.

A server can replace the remembered name via setup's auth option, or clear it via `set steam_auth_profile DELETE`. The setting is manager metadata and must never enter game config_sync_keys or exports. Profile-name validation uses a public function in the existing auth module; passwords/tokens are never server settings.

## Setup ordering

Reject conflicting explicit selectors before configure. Configure and enforce platform/host/port prerequisites as today. Before module.install, guard stopped state, load the module recipe and satisfy missing files through the selected source. Do not call module.install if acquisition/import fails. Preserve existing setup --assets semantics and transactional importer ownership. Remember the profile only once the file phase succeeds; failure retains any previous saved selection.

## Steam library resolver

A focused utils/steam_library.py reads public appmanifest_APPID.acf and libraryfolders.vdf only. Resolve a client/SteamLibrary root containing steamapps; follow declared modern nested or legacy numbered library paths, deduplicating canonical roots and skipping unavailable mounted libraries. An explicit steamapps path restricts lookup to that library and resolves duplicates. Reject duplicate matching installs, malformed or oversized metadata, mismatched app IDs, nonregular/linked metadata, and installdir path escapes. Do not recursively scan Steam, read loginusers/config.vdf, or copy auth data. Conventional root symlinks may be resolved; game content still follows the strict existing importer link/ownership policy.

Use a bounded KeyValues subset parser for quoted keys/values, braces, whitespace and line comments, with escaped quotes/backslashes and nested mappings. No includes, directives, arbitrary code, or new dependency is required. Valve's primary KeyValues implementation reference: https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/tier1/KeyValues.cpp.

## Cache bug and verification

Real login placed cache under profile/home/Steam/config/config.vdf. Accept that known path and the legacy runtime/config/config.vdf without moving or exposing cache files. Synthetic regression tests cover both. Full unit and lint gates follow all changes; auth/lib/source/parser/setup orchestration tests remain credential-free. Local Q3 acquisition may resume afterward using the already authorized SSD tag/profile. No other game downloads in parallel and no CI credential integration.

## Server payload and content policy (user clarification)

Every campaign row should leave checked-in reusable setup/acquisition/import code, not only a manually prepared local tree. Default installs keep a runnable dedicated server plus the fullest compatible server content available from the declared legitimate source: maps, packages, scripts, required libraries and supporting data. Minimum readiness sentinels are not the complete selection. Disposable full-client acquisition staging is removed; known unrelated client executables/renderers are not installed. Owned content archives are retained whole rather than stripping their maps or companion resources.

For Q3, the existing nine PK3 allowlist preserves all base-game/patch content (36 distinct BSP maps observed locally). Tighten the public ioquake3 engine installation with an additive exact relative-file exclusion option in the shared archive copier, used only by Q3. Exclude the known client executable, renderer libraries and client-only cgame/UI engine modules; retain dedicated executable, base/missionpack server game modules, config, all PK3s/maps and all other supporting files. Other module installs keep existing behavior. Do not delete untracked operator files from existing installations. Validate fresh synthetic payload selection and then the dedicated-only SSD engine through AlphaGSM readiness/query/info/stop again.
