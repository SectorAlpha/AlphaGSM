# AlphaGSM Skill Packaging

The [canonical catalogue](../SKILLS.md) lists all skills by task. Start with
`alphagsm-agent-operations` for running servers or `alphagsm-agent-development`
for repository maintenance.

Use [server-requirements](alphagsm-server-requirements/SKILL.md) before provisioning
or dependency-related repairs. Its [installation policy](alphagsm-server-requirements/references/approval-gates.md)
distinguishes new software from ordinary managed work and ambiguous server intent.

Each directory contains a `SKILL.md` with YAML `name` and `description`, followed
by focused instructions. Names match directories. Canonical files stay here so
existing documentation links remain stable. `.agents/skills/<name>` contains a
relative directory symlink to `../../skills/<name>` for native repository
discovery; maintain one instruction source.

Agents with shell access can use these workflows in the selected AlphaGSM
installation. Other agents can load files explicitly from [SKILLS.md](../SKILLS.md).
When Git checks symlinks out as plain text files, native discovery is unavailable;
use explicit loading or a checkout with symlink support. The validator accepts
valid Git link stubs and reports this limitation.

Keep descriptions concise and specific. Link supporting references only when
needed, and use Markdown links for local files so validation can check them.
Read [AGENTS.md](../AGENTS.md) for authoritative repository contracts: canonical
top-level game modules are package-backed, module assets stay colocated, and
server content is multiplayer dedicated-server content by default.

Run `make skills-check` after editing. Structural validation checks metadata,
catalogue membership, inline local Markdown references and discovery targets.
Evaluate actual task behavior separately using
[skill-maintenance](alphagsm-skill-maintenance/SKILL.md). Full authoring and check
details are in [DEVELOPERS.md](../DEVELOPERS.md).
