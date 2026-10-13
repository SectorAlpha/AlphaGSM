# Don't Starve Together

This guide covers `dstserver`, supported as `ENABLED (AUTH)`. Server files install
anonymously through SteamCMD,
but online startup requires a valid Klei cluster token and cluster configuration.
The process and Docker lifecycle tests are configurable with that prerequisite;
the new Workshop load checks remain pending a credentialed live run.

## Requirements

- A Klei account and valid dedicated-server `cluster_token.txt`
- `cluster.ini` and the selected shard's `server.ini`
- `screen` for the process runtime, or Docker and the SteamCMD Linux runtime image
- SteamCMD libraries (`lib32gcc-s1`, `lib32stdc++6`) and `requirements.txt`

Follow [Klei's dedicated-server settings guide](https://kleiforums.com/forums/topic/64552-dedicated-server-settings-guide/)
for the cluster configuration. Treat the token as a secret.

## Quick Start

```bash
alphagsm mydstserver create dstserver
alphagsm mydstserver setup
```

Before starting, place your Klei token and configuration in this layout:

```text
<install_dir>/DoNotStarveTogether/mydstserver/
├── cluster_token.txt
├── cluster.ini
└── Master/
    └── server.ini
```

Then run:

```bash
alphagsm mydstserver start
alphagsm mydstserver status
alphagsm mydstserver query
alphagsm mydstserver info
alphagsm mydstserver stop
```

AlphaGSM uses `-persistent_storage_root <install_dir>`,
`-conf_dir DoNotStarveTogether`, `-cluster mydstserver`, and `-shard Master`.
Changing `confdir`, `cluster`, or `shard` selects a different configuration tree.
One AlphaGSM instance starts one shard; configure additional shards separately.

## Ports

AlphaGSM claims and publishes three UDP ports, and syncs them into the selected
shard's `server.ini` before startup:

| AlphaGSM setting | Native setting | Default |
| --- | --- | --- |
| `port` | `[NETWORK] server_port` | 10999 |
| `queryport` | `[STEAM] master_server_port` | 27016 |
| `authport` | `[STEAM] authentication_port` | 8766 |

`query` and `info` use the Steam query port. Existing shard settings are retained
while these port values are synchronized; the cluster token is untouched.
[Klei documents the corresponding native port options](https://support.klei.com/hc/en-us/articles/360029556192-Dedicated-Server-Command-Line-Options-Guide).

## Workshop Mods

Add a public dedicated-server-compatible item by its ID or Workshop URL:

```bash
alphagsm mydstserver mod add workshop 'https://steamcommunity.com/sharedfiles/filedetails/?id=378160973'
alphagsm mydstserver mod list
alphagsm mydstserver mod apply
alphagsm mydstserver start
```

[Global Positions](https://steamcommunity.com/sharedfiles/filedetails/?id=378160973)
is the small multiplayer fixture used by the validation workflow. Workshop items
are validated against DST game ID `322330`; the dedicated-server tool ID is
`343050`. Collections use `mod add workshop-collection ID_OR_URL` and expand to
validated items.

AlphaGSM writes native `ServerModSetup` declarations in
`mods/dedicated_server_mods_setup.lua` and enables the desired items in the selected
shard's `modoverrides.lua`. Downloads alone do not enable a mod. Application is
automatic before startup unless `mods autoapply` is disabled. A running server
needs a restart to load configuration changes.

```bash
alphagsm mydstserver mod remove workshop 378160973
alphagsm mydstserver mod apply
# Or restore all AlphaGSM-managed Workshop declarations:
alphagsm mydstserver mod cleanup
```

AlphaGSM retains the original operator Lua configuration and restores it on
cleanup. If a managed file changes outside AlphaGSM, application fails rather
than overwriting that edit. Cleanup removes activation declarations, leaving
native downloaded caches in place. Mods required in multiple shards must be
configured for each shard.

## Validation With Your Klei Cluster

Supply the directory containing `cluster.ini`, `cluster_token.txt`, and
`Master/server.ini`. Validation copies only those configuration files and optional
world-generation settings into a new disposable install. It uses a single fresh
Master world with sharding disabled. Existing worlds, saves, mod overrides, and
logs are not copied, and the source cluster is unchanged. Use a token appropriate
for this test server; the disposable directory still contains its private token.

Process and Docker integration:

```bash
PYTHONPATH=.:src \
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 ALPHAGSM_RUN_WORKSHOP=1 \
ALPHAGSM_DST_CLUSTER_SOURCE='/private/path/to/cluster' \
ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX=alphagsm-steamcmd-linux-runtime:workshop \
python -m pytest tests/integration_tests/test_dstserver.py -v -s
```

Build the branch's `docker/steamcmd-linux` image with that tag before using the
example Docker override. Streamed process smoke:

```bash
ALPHAGSM_DST_CLUSTER_SOURCE='/private/path/to/cluster' ALPHAGSM_RUN_WORKSHOP=1 \
make smoke-test SMOKE_TEST=run_dstserver.sh
```

The Workshop check requires the fresh native shard log to show execution of
`workshop-378160973`'s `modmain.lua`, followed by a successful Lua bootstrap without
mod errors. It then requires online startup, actual A2S query/info results, and
shutdown. Download messages or files on disk alone do not pass. Without a cluster
fixture the test reports the missing prerequisite; startup or load timeouts fail.

## Useful Commands

```bash
alphagsm mydstserver update
alphagsm mydstserver backup
```

<!-- alphagsm-server-variables:start -->

## Server variables

```bash
alphagsm mydstserver set --list
alphagsm mydstserver set queryport 27017
alphagsm mydstserver set authport 8767
```

The game port and these two Steam ports must be unique for every local shard.

<!-- alphagsm-server-variables:end -->
