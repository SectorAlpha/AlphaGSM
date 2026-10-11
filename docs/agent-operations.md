# Run AlphaGSM With An AI Agent

An AI agent with terminal access to your AlphaGSM installation can create,
configure, run, check, back up and maintain your servers using the same commands
you use yourself. The repository includes 35 skills covering server operation
and development. The [skill catalogue](../SKILLS.md) lists them all.

## Get started

Open this repository in your agent and give it access to the host where AlphaGSM
is installed. Tell it which server to work on and what result you want. If you
use a separate installed AlphaGSM binary or config, give it that location too.

For server management, ask it to use `alphagsm-agent-operations`. For code changes,
ask it to use `alphagsm-agent-development`. These entry skills select the focused
workflows needed for your request.

Codex can discover the skills through `.agents/skills/`, which links to the
maintained files under `skills/`. If your agent does not discover them, ask it to
read `SKILLS.md` and the selected skill directly. On a Windows checkout where
Git turns symlinks into text files, use this explicit loading method. Native
discovery requires working directory links. See
[official skill guidance](https://learn.chatgpt.com/docs/build-skills).

## Example requests

- “Use alphagsm-agent-operations. Create Minecraft Vanilla as mymc in
  /srv/alphagsm/mymc on port 25565. Start it, check that it answers, and leave
  it running.”
- “Check mytf2. Explain why its game query fails and repair the cause.”
- “Back up mymc and tell me which archive was created and what it includes.”
- “Install MetaMod and SourceMod on mytf2, then verify that the server loads
  them and answers queries.”
- “Update first and second, keep them running afterward, and report each result.”
- “Enable mymc on reboot, but leave it stopped today.”
- “Use alphagsm-agent-development. Fix this integration failure and open a PR
  on the latest default branch.”

Use an existing tag for repeated requests. The agent should inspect and reuse
its state rather than recreate it or overwrite saves. Give the exact archive
when restoring and the exact server/world scope when resetting progress.

## What to expect

The agent checks the selected host, configuration and game requirements before
making changes. It uses AlphaGSM for the lifecycle and verifies actual game
readiness. A running process alone is not a healthy server. It reports the
resulting running state, meaningful checks, backup/recovery artifacts and any
remaining blocker. Fleet results are reported per server.

For a code change, it follows the repository's lifecycle, runtime and support
contracts, updates tests/docs/changelog as needed, and includes executed
validation in the requested PR. Preparing a release is a separate request from
publishing it.

Some games require your provider login, token or license (**ENABLED (AUTH)**).
Others need owned assets, exported files, a download URL or a local service
(**ENABLED (BYO)**). The agent explains the missing requirement; the skills do
not supply it. Keep credentials out of prompts, logs and shared reports; use
the installation's supported private configuration path.

The library supplies reusable instructions. To run tasks, the agent needs the
host tools and permissions required by those tasks. Ongoing monitoring needs
an explicitly requested scheduler; these skills do not start a persistent
agent service. See [Everyday Commands](commands.md) for the underlying commands.
