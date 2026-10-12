# Docker choice and installation approval

These are mandatory agent gates for operations and development. They apply
before direct and indirect installations, including inside virtualenvs, user
directories, manager containers and image builds.

## First-use Docker decision

Prefer Docker for game servers. Prefer the repository's containerized manager
when setup would otherwise need host Java, SteamCMD or other tooling. On first
use on the selected host/config, ask the user before starting the manager or any
game container. Existing Docker/config/images are not evidence of consent.

Present the actual topology, server scope, image sources, mounts, ports and any
missing installation plan. For example: “May I use the AlphaGSM manager and
Minecraft containers on this host, using the repository images and the host
Docker socket, with server data under /srv/alphagsm? The following images are
missing; may I acquire them through this pull/build plan?” Wait for the reply.

Keep the approval and its host/config/topology/server scope in the task evidence
or a private handoff. Reuse it within that scope; do not ask on every restart.
First-use consent does not authorize switching an existing process fleet to a
global Docker backend or installing later-discovered dependencies. A new host,
topology or wider server scope requires a new decision.

If Docker or Compose is absent, prepare the appropriate host installation plan
and ask before installing. Docker-in-Docker still needs a working container
executor; it cannot solve a missing Docker engine by itself. Never silently
fall back to host runtime installations. If the user chooses host execution,
apply the same installation gate to every missing host dependency.

The [checked-in manager](../../../docs/docker-manager.md) uses the host daemon
through its socket to launch sibling game containers (Docker-outside-of-Docker).
It includes setup-time tooling inside the manager. True Docker-in-Docker uses a
separate nested daemon and is not supplied by the checked-in Compose deployment.
If requested, explain that limitation and obtain a separate topology/privilege
decision; do not invent a supported DinD flow or launch an arbitrary `docker:dind`
image. Missing daemon permissions are not permission to use sudo, alter socket
permissions, add groups or launch privileged containers.

## AlphaGSM image origin

Use only AlphaGSM images published by, or built from,
`https://github.com/SectorAlpha/AlphaGSM`. The repository defines:

- Manager: `ghcr.io/sectoralpha/alphagsm`, in
  [manager Compose](../../../docker/manager/compose.yml).
- Game families: `ghcr.io/sectoralpha/alphagsm-<family>-runtime`, for the six
  families in [runtime defaults](../../../src/server/runtime.py) and
  [the publishing workflow](../../../.github/workflows/build-runtime-family-images.yml).
- Local builds: the matching checked-in Dockerfile and inspected checkout
  context, recording repository origin, commit, relevant local changes,
  Dockerfile and resulting image ID.

Check effective config, module and environment image overrides before wrapper
startup and game start. Reject unrelated third-party replacements; do not run
them and inspect afterward. Verify package/repository provenance, capture the
resolved tag/digest and source labels when available, and do not treat a familiar
local tag or a label alone as provenance. If a cached image's origin cannot be
established, mark it unknown and propose a verified official pull or local build.
The official Dockerfiles' upstream base images and package sources are reviewed
build inputs; this rule concerns AlphaGSM manager/game images.

## New package or dependency installation

**Always ask the user and wait for explicit approval of the concrete plan before
installing a new package or dependency.** A request to run, fix, provision,
upgrade, test or “install whatever is needed” is not approval of a newly
discovered dependency plan. Urgency, noninteractive flags, sandbox approval or a
successful prior install do not bypass this gate.

The plan must identify the reason/game/version, packages/runtime/image and
available pins, authoritative source, destination (host/venv/container/image),
exact commands/helper and transitive installs, required privileges, network and
expected storage/downtime implications. Do not fabricate versions or estimates.
Include package-manager replacements/upgrades/removals in the plan when needed.
One explicit reply may approve a fully described batch and Docker first use;
retain that scope and ask again for additions, changed sources or destinations.

This includes apt/dnf/brew/winget, pip/npm/venv dependencies, compiler toolchains,
SteamCMD bootstrap, Wine/Proton/.NET/Java, mod/plugin prerequisites, new runtime
image pulls/builds, and scripts/Make targets that perform these indirectly.
Inspect wrapper fallback paths: [alphagsm-docker](../../../alphagsm-docker) can
pull or build/start the manager; AlphaGSM `start` can build a missing default
runtime image. `setup`, `update`, `mod apply`, test runners and `make deps` can
also install prerequisites. Do not invoke them to discover what is missing.

Wrapper `up/start` forces manager refresh and attempts a release pull even if a
verified image is cached; developer mode rebuilds. Forwarded commands can
start/recreate a missing or stale manager too. For reuse-only work, inspect and
choose a path proven to reuse the already running verified manager; do not call
`up` as a harmless ensure step. Otherwise obtain approval for the refresh and
the complete pull/build fallback, or use an inspected path limited to the
approved action. The default direct Compose/manager entrypoint eagerly pulls
all runtime families; the wrapper defaults that off. For a manager plus one-game
batch, explicitly keep `ALPHAGSM_PULL_RUNTIME_IMAGES=0`, or include every eager
pull in the approved plan.

Ordinary game-file downloads within a requested lifecycle remain authorized
once the inspected path has no unapproved dependency installation. Reusing
verified existing dependencies/images and read-only checks needs no install
approval. If a dependency installer might self-update, disclose that in its plan.
For example, approve the selected SteamCMD invocation's possible client update
once within the described batch; reusing a file does not prove it will stay
unchanged. Compiling requested game source with an already verified toolchain
is game provisioning; installing a compiler/library is a dependency installation.
An image build still requires approval even if its tools already exist on the host.
Do not accept EULAs or provide AUTH/BYO inputs on the user's behalf.

When approval is pending or declined, stop dependent installation/setup/start,
continue independent read-only work and report the exact blocker. Silence is not
consent. After approval, execute only that plan, verify installed requirements
and re-check effective runtime before continuing. Unexpected extra dependencies
require another approval; do not chain an installer retry into a broader install.
