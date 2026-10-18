# Optional first-run setup

After installing AlphaGSM, run it in a terminal without a command:

```sh
./alphagsm
```

On the first such launch, AlphaGSM offers a guided tour. Press Enter to skip it,
or type `y` to begin. Skipping or finishing the tour is remembered for your
configured AlphaGSM operator home. Existing installations also see this offer on
their next bare interactive launch after upgrading.

Replay or skip explicitly at any time:

```sh
./alphagsm --welcome
./alphagsm --skip-welcome
```

The skip command also works in installation scripts. Normal server commands,
agent commands, help and version output run directly. Redirected input or output
does not trigger the first-run offer; an explicit `--welcome` requires terminal
input and output. Bare noninteractive launches retain the normal help/usage exit
status of 2.

## What the tour offers

1. **Create/configure a game server.** Choose a game module (`?` lists the available
   modules), then a new local name such as `my-minecraft`. Review the exact command
   and confirm creation. This only creates its local record. A separate question
   offers to run the usual `setup`, which can download files or install a runtime
   and asks for the game's settings. Decline to do that later. The tour never
   starts the game. Existing names, command names, wildcards and all-number names
   cannot be used to create a server through the tour.
2. **Everyday commands.** See how to set up, start, check and stop a server without
   running any commands. See [Everyday Commands](commands.md) for more details.
3. **Optional Sector Alpha connection.** Confirm before opening the existing
   enrollment/binding wizard. It contacts `https://sector-alpha.net` for onboarding;
   later stats and execution use `https://gameserver-api.sector-alpha.net`;
   obtain the enrollment code from your account at `https://sector-alpha.net`.
   That wizard previews the servers/endpoints and asks for binding permissions.
   See [Optional Sector Alpha connection](sector-alpha-agent.md).

Press Enter or `s` at the menu to finish. Blank game/name answers cancel that
step. Ctrl+C or end-of-input cancels without running further commands; anything
you already approved and completed remains in place. Cancelling before finishing
leaves a first-run offer pending unless you already skipped or completed it.
A failed create/setup stops the tour and reports the failure so you can retry
the command shown.

## Reporting and permissions

The tour never enables remote reporting or management. New installations keep
both off. Public listings require separate per-server approval, and reporting
still needs an explicit `agent enable-reporting` command. Existing remote
permissions remain in force when you replay the tour. Choosing local setup,
viewing commands or skipping does not contact Sector Alpha.

The remembered tour choice is a small local `welcome-v1.done` file under your
configured AlphaGSM home (normally `~/.alphagsm`). It contains only `skipped` or
`completed`; it holds no account information, credentials or permission choices.
Use `--welcome` to replay without deleting it.
