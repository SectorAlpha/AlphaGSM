# Running AlphaGSM In Docker

This is an optional deployment mode.

AlphaGSM can still run directly on the host exactly as before. This guide is
only for the case where you want AlphaGSM itself to run in a Docker container
while still launching game-server containers through the host Docker daemon.

## How This Works

Use Docker-outside-of-Docker:

- run one AlphaGSM "manager" container
- mount the host Docker socket into it
- let AlphaGSM call the host Docker daemon through the normal `docker` CLI
- keep server data on a host path that is mounted into the manager container at
  the same absolute path
- let the manager container authenticate to GHCR and pre-pull the AlphaGSM
  runtime-family images
- keep enough local tooling in the manager container for setup flows that still
  do preparatory work before the runtime container starts, such as Java-based
  Minecraft jar bootstrap

The last point matters because AlphaGSM stores server install paths and later
passes them back into `docker run -v ...` when starting Docker-backed game
servers. If AlphaGSM stores `/srv/alphagsm/servers/mymc`, the host Docker
daemon must also be able to see that exact path.

## What Stays The Same

- direct host installs still work
- the default configuration still uses the traditional process runtime unless
  you choose otherwise
- this manager-container setup is separate from the runtime-family images under
  `docker/java/`, `docker/steamcmd-linux/`, and the other family directories

## Files In This Repository

- `docker/manager/Dockerfile`
- `docker/manager/compose.yml`
- `docker/manager/alphagsm.conf.example`
- `alphagsm-docker`

## Quick Start Wrapper

From the repository root you can use the wrapper script instead of typing the
full Compose command each time:

```bash
./alphagsm-docker up
./alphagsm-docker start
./alphagsm-docker stop
./alphagsm-docker ps
./alphagsm-docker mymc create minecraft.vanilla
./alphagsm-docker mymc setup -n 25565 "$PWD/.alphagsm-docker/servers/mymc"
./alphagsm-docker mymc start
./alphagsm-docker mymc connect
```

`start` is an alias for `up`, and `stop` is an alias for `down`.

The script will:

- create a Docker-manager state directory if it does not exist
- write `alphagsm.conf` there from the manager example config
- default to release mode, which tries to pull `ghcr.io/sectoralpha/alphagsm:latest` and falls back to a local build if that pull fails
- support `./alphagsm-docker up --develop` or `./alphagsm-docker start --develop`, which switches the state dir into developer mode and always rebuilds the manager image locally
- reuse the existing running manager container for forwarded AlphaGSM commands instead of rebuilding on every exec
- recreate a stopped manager container from the active mode without forcing the other mode's image path
- build bundled AlphaGSM runtime-family images locally on demand when their default GHCR tag is missing, so quick-start still works without registry auth
- provide wrapper-native `./alphagsm-docker ps` and `./alphagsm-docker <server> connect` commands that read local server metadata instead of forwarding through manager `exec`
- forward any other arguments to `python alphagsm ...` inside the manager container

Because `./alphagsm-docker ps` reads local JSON server config, it still
requires a working host `python3`. For Docker-backed servers, wrapper
`connect` also uses that host metadata when it is available; otherwise the
wrapper falls back to AlphaGSM's normal forwarded `connect` command.

When a game module prompts for an install directory and you accept the default
inside manager-container mode, AlphaGSM now prefers `ALPHAGSM_HOME/servers/<name>`
instead of `/root/<name>`.

The wrapper defaults `ALPHAGSM_PULL_RUNTIME_IMAGES=0` so quick-start users do
not need GHCR credentials just to bring the manager container up. If you do
want eager runtime image pulls at startup, run:

```bash
ALPHAGSM_PULL_RUNTIME_IMAGES=1 ./alphagsm-docker up
```

If you are actively developing this repository and want manager restarts to
always use the local checkout, use:

```bash
./alphagsm-docker start --develop
```

That mode is stored in the wrapper state directory, so later `./alphagsm-docker`
commands keep using local manager rebuilds until you switch back with a plain
`./alphagsm-docker start` or `./alphagsm-docker up`.

By default it uses a repo-local state path:

```bash
$PWD/.alphagsm-docker
```

Override that with `ALPHAGSM_HOME` if you want a different shared path:

```bash
ALPHAGSM_HOME=/srv/alphagsm ./alphagsm-docker up
```

Keep Docker-backed server install paths under that same `ALPHAGSM_HOME` path so
the host Docker daemon and the manager container see the same absolute path.

## Host Preparation

Create the shared host directory:

```bash
sudo mkdir -p /srv/alphagsm
sudo chown "$USER":"$USER" /srv/alphagsm
cp docker/manager/alphagsm.conf.example /srv/alphagsm/alphagsm.conf
```

The example config keeps all AlphaGSM state under `/srv/alphagsm` and selects:

- `[runtime] backend = docker`
- `[process] backend = subprocess`

That is intentional. Inside the manager container, Docker-backed servers are the
main use case.

## Start The Manager Container

From the repository root:

```bash
docker compose -f docker/manager/compose.yml up -d
```

If your host still uses the standalone Compose binary, use:

```bash
docker-compose -f docker/manager/compose.yml up -d
```

This mounts:

- `/var/run/docker.sock` so AlphaGSM can launch sibling containers
- `${ALPHAGSM_HOME:-/srv/alphagsm}:${ALPHAGSM_HOME:-/srv/alphagsm}` so stored
  server paths are valid both inside the manager container and on the host
  daemon
- `${HOME}/.docker:/root/.docker:ro` so existing Docker registry credentials can
  be reused inside the manager container

The manager image also includes Java and the Docker CLI. That is intentional:
some Docker-backed modules still perform local setup-time work, then hand off
the actual long-running server process to a sibling runtime container.

The checked-in Compose file now defaults to `ghcr.io/sectoralpha/alphagsm:latest`
and is configured to prefer pulling a fresh `latest` image before reusing a
local copy. If you explicitly want a local rebuild with direct Compose instead
of the wrapper, add `--build`.

On startup, the manager container will try to pull the runtime-family images
referenced by `src/server/runtime.py`.

If your host Docker config already has GHCR credentials, the read-only
`${HOME}/.docker` mount is enough.

If you prefer explicit environment variables, start Compose like this:

```bash
export GHCR_USERNAME=your-github-username
export GHCR_TOKEN=your-ghcr-token
docker compose -f docker/manager/compose.yml up -d --build
```

Set `ALPHAGSM_PULL_RUNTIME_IMAGES=0` if you want to skip the eager pull and let
AlphaGSM pull images lazily when a server starts.

## Run AlphaGSM Inside The Manager Container

Create a server:

```bash
docker compose -f docker/manager/compose.yml exec alphagsm \
  python alphagsm mymc create minecraft.vanilla
```

Set it up under the shared host path:

```bash
docker compose -f docker/manager/compose.yml exec alphagsm \
  python alphagsm mymc setup -n -l 25565 /srv/alphagsm/servers/mymc
```

Start it:

```bash
docker compose -f docker/manager/compose.yml exec alphagsm \
  python alphagsm mymc start
```

Replace `docker compose` with `docker-compose` on hosts that do not have the
Compose plugin installed.

If you use `./alphagsm-docker`, it will do the same `exec` flow for you.

The game server container will be created by the host Docker daemon, not by a
nested daemon inside the manager container.

## Important Rules

1. Keep all Docker-managed server install paths under `ALPHAGSM_HOME` or another
  host directory mounted into the manager container at the exact same absolute
  path.
2. Do not use container-only paths like `/tmp/server` for Docker-backed servers.
3. If you try to start a Docker-backed server from a container-only path such as
  `/root/scp`, AlphaGSM now hard-fails before `docker run` with a path-identity
  error instead of launching a broken child container.
4. If you want to pull private GHCR images, log Docker into the registry on the
  manager side so the mounted Docker socket can reuse those credentials. The
  sample manager setup supports either mounting `${HOME}/.docker` or passing
  `GHCR_USERNAME` and `GHCR_TOKEN`.

## Security Note

Mounting `/var/run/docker.sock` gives the manager container broad control over
the host Docker daemon. Treat this as a trusted-admin deployment pattern.

## Outside Docker Still Works

Nothing in this setup replaces the normal host workflow. If you want to keep
running AlphaGSM directly on the host, continue using the normal install and
config flow from `README.md`.
