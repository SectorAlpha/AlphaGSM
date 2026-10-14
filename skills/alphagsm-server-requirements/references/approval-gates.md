# New software installation and server intent

The only hard approval gate in this agent policy is **installing new software**.
Clarifying an ambiguous request establishes what to do; it is not an extra
approval gate for ordinary AlphaGSM operations.

## Resolve the request for every game type

List the selected user's servers and inspect their actual installation state.
Resolve canonical modules and aliases before matching; include family variants
and use the exact host/config. A registered tag without usable server files is
not a completed installation.
For a specific variant, match that canonical type; for a broad family request,
retain the installed variants rather than treating them as interchangeable.
Read-only requirements/health requests stay read-only and do not need an
installation question merely because something is absent.
That scope includes the manager: forwarded wrapper diagnostics can create state,
pull/build images or start/recreate it. For inspection-only work, use verified
existing-manager diagnostics or source/config inspection and report unavailable
checks. Managed installation freedom applies to requested operational work,
not unsolicited changes during an assessment.

| User request and state | Next action |
| --- | --- |
| “Run a TF2 server”; no TF2 installation | Ask to install TF2, naming the tag/path, Docker plan and required new external host software; wait for the reply |
| “Run a TF2 server”; TF2 already installed, action unspecified | Clarify whether to start the existing server, create another, or change it; do not assume a healthy/running server satisfies the request |
| More than one matching installation, target unspecified | Clarify the target as well as the intended action |
| “Start mytf2”, “restart mymc”, or another explicit action on an identified existing server | Perform it through AlphaGSM; no separate startup, Docker, topology or dependency-refresh approval |
| Explicit installation request or approved installation plan | Install through the supported AlphaGSM workflow without asking again for its managed steps |

TF2 is an example: apply the same decisions to every game server type. For an
incomplete installation and a vague request, ask whether to finish installing
it. For an explicit repair/setup request, follow that requested workflow.
Only ask further if the target/action is unclear or new external software is
needed outside the approved installation scope. A requested extra server is a
new installation; an explicit request to install that extra server authorizes it.

## AlphaGSM-managed work proceeds

AlphaGSM's own code and supported installation mechanisms are fair game within
the requested task. Do not add approval blockers for its commands, helpers,
configuration, tests, manager/runtime image pulls or builds, dependency refreshes
inside repository images, project-local pinned Python requirements, or supported
mod/plugin prerequisites. The approved server installation includes the managed
steps of its repository recipe, such as SteamCMD bootstrap in manager/data paths.
A supported SourceMod request includes its required MetaMod; use the actual
manifest/helper dependency wiring rather than inventing dependencies.

Prefer the containerized AlphaGSM manager and Docker game runtimes. Use existing
Docker without a first-use consent question. Explain the chosen deployment in
the task update and preserve the requested server/fleet scope. AlphaGSM's
[manager deployment](../../../docs/docker-manager.md) uses the host socket and
sibling containers; true Docker-in-Docker is not supplied by the checked-in
Compose file. Describe actual capability accurately and use the supported path
where appropriate; do not turn that technical distinction into an approval gate.

Use only AlphaGSM images published by, or built from,
`https://github.com/SectorAlpha/AlphaGSM`:

- Manager: `ghcr.io/sectoralpha/alphagsm`, defined in
  [manager Compose](../../../docker/manager/compose.yml).
- Games: `ghcr.io/sectoralpha/alphagsm-<family>-runtime`, defined in
  [runtime defaults](../../../src/server/runtime.py) and
  [the publishing workflow](../../../.github/workflows/build-runtime-family-images.yml).
- Local builds: matching checked-in Dockerfiles from the inspected repository
  context; record commit, relevant changes and resulting image identity.

Inspect image overrides and use a compliant repository image instead of an
unrelated replacement. If a cached image's origin is unknown, obtain/build the
repository image as an ordinary managed step. Wrapper refresh/pull/build fallback
and runtime lazy builds need no additional approval. The direct manager entrypoint
can eagerly pull all runtime families; prefer `ALPHAGSM_PULL_RUNTIME_IMAGES=0`
when only one game is needed to avoid unnecessary downloads. These are execution
choices, not permission gates. Official Dockerfiles' upstream build inputs are
part of those repository builds.

## Ask before genuinely new external software

Always ask and wait before installing new software outside AlphaGSM's managed
installation scope. Examples include a missing host Docker engine/Compose,
host Java/.NET/Wine, a compiler or archive tool, and unrelated packages/plugins
not provided by the requested repository workflow. A script living in this
repository does not by itself authorize changes to the host's system packages.
Inspect Make targets and helpers for such effects before running them.

Identify the software/source, purpose, destination and command, with meaningful
privilege/resource effects. A fresh-server installation question can include
these host requirements in one plan. Reuse explicit installation approval for
that scope; ask again only for additional new external software. Existing tools,
ordinary upgrades of the installed game, existing-server starts/restarts/settings
and AlphaGSM-managed components need no installation approval loop.

If new software approval is pending or declined, pause that installation and
its dependent work, while continuing independent work. Missing credentials,
owned assets, access or unsupported platforms remain real prerequisites to
resolve, not permission gates to invent. Honor actual licenses and user intent;
do not fabricate inputs or claim success without health evidence.
