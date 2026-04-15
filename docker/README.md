## Runtime Family Images

These directories are the in-repo scaffolds for the Docker runtime families
referenced by `src/server/runtime.py`.

The optional AlphaGSM manager-container scaffold lives separately under
`docker/manager/`. That setup is for running AlphaGSM itself in Docker while it
launches sibling game-server containers through the host Docker socket. It does
not replace the direct host install path.

Current family mapping:

- `java` -> `docker/java/`
- `quake-linux` -> `docker/quake-linux/`
- `service-console` -> `docker/service-console/`
- `simple-tcp` -> `docker/simple-tcp/`
- `steamcmd-linux` -> `docker/steamcmd-linux/`
- `wine-proton` -> `docker/wine-proton/`

Legacy aliases still accepted by the runtime layer:

- `minecraft` -> `java`
- `ts3` -> `service-console`

These scaffolds are published by the manual GitHub Actions workflow at
`.github/workflows/build-runtime-family-images.yml`. The runtime metadata now
defaults to the GHCR `latest` tags, for example
`ghcr.io/sectoralpha/alphagsm-java-runtime:latest`, while the workflow still
publishes an additional versioned tag for traceability.

The images are intentionally split by runtime family rather than by individual
game module. Modules should describe their family-specific env, mounts, ports,
and command via `get_runtime_requirements(...)` and `get_container_spec(...)`.
