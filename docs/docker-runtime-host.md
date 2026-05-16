# Run Docker-Backed Servers From Host AlphaGSM

This guide is for the direct host install.

Use it when you want AlphaGSM itself to run on the machine normally, but you
want individual game servers to run as Docker containers instead of screen-backed
host processes.

This is not the same as [Run AlphaGSM In Docker](docker-manager.md), where the
whole AlphaGSM manager runs inside a container.

## What This Mode Does

With `[runtime] backend = docker`, AlphaGSM still handles the normal server
lifecycle:

- `create`
- `setup`
- `start`
- `status`
- `query`
- `info`
- `stop`

The difference is that `start` launches a Docker container for modules that
expose Docker runtime metadata.

## What You Need

You need:

- a normal host install of AlphaGSM
- a working host Docker CLI and daemon
- permission to run `docker` as your user
- a game module that supports the Docker runtime hooks

AlphaGSM can still use the normal process runtime for modules that are not set
up for Docker.

## 1. Configure The Runtime Backend

Copy the config if you have not done that yet:

```bash
cp alphagsm.conf-template alphagsm.conf
```

Then set the runtime backend:

```ini
[runtime]
backend = docker
```

AlphaGSM resolves the effective runtime per server. If the module exposes Docker
metadata, AlphaGSM will store the resolved runtime fields in that server's JSON
datastore during `create` / `setup`.

## 2. Create And Set Up A Server

Example with Minecraft Vanilla:

```bash
./alphagsm mymc create minecraft.vanilla
./alphagsm mymc setup
```

Keep the install path on a normal host-visible path such as:

```bash
/srv/alphagsm/servers/mymc
```

For a direct host install, there is no same-path manager-container requirement.
The main rule is that the host Docker daemon must be able to bind-mount the path
you choose.

## 3. Check The Runtime Before Start

Use the built-in doctor command:

```bash
./alphagsm mymc doctor
```

This prints the effective runtime decision and, for Docker-backed servers,
includes:

- configured backend
- module runtime preference
- resolved runtime family
- image and container name
- Docker CLI health
- local image presence
- current container state

If Docker is configured but the module still resolves to `process`, the doctor
output will show that clearly.

## 4. Start And Check The Server

```bash
./alphagsm mymc start
./alphagsm mymc status
./alphagsm mymc query
./alphagsm mymc info
```

## 5. Stop It Later

```bash
./alphagsm mymc stop
```

## Notes

- AlphaGSM uses the runtime-family image declared by the module or the shared
  family defaults in `src/server/runtime.py`.
- If a default AlphaGSM runtime-family image tag is missing locally, AlphaGSM
  can build the matching in-repo Dockerfile on demand.
- Docker-backed servers still keep their AlphaGSM metadata under the normal
  server datastore path.
- `doctor` is the fastest way to tell whether a server is actually resolving to
  Docker, which family/image it will use, and whether the local host can launch
  it cleanly.