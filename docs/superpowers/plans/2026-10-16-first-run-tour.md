# Optional first-run AlphaGSM tour

Offer the tour only on a bare interactive launch with terminal input and output,
once per configured operator home. Enter skips and remembers that choice.
--welcome explicitly replays it; --skip-welcome explicitly records the opt-out.
Help, version, server/agent commands, workers, services and redirected/scripted
invocations retain their existing paths and never trigger the tour.

The tour offers common-command guidance, local server creation with an exact
preview and confirmation, a separate confirmation before existing setup can
download/install anything, and an optional Sector Alpha enrollment/binding flow
with its own explicit network confirmation. It never starts a game or enables
reporting/management automatically. Existing remote consent is preserved.

Keep the non-secret versioned preference separate from server and agent config.
Create its marker exclusively without following symlinks. Existing server names
must be rejected before creation and rechecked under the normal state lock.
Game/tag input passes canonical catalogue/strict local-name validation, and all
commands reuse core dispatch with argv arrays; no shell execution.

- [x] Observe first-run/skip/replay/script compatibility and consent tests fail.
- [x] Implement small welcome/state modules and top-level routing/help.
- [x] Verify local creation, existing-data preservation, cancellations, unsafe
  marker paths and explicit remote/setup approvals with isolated state.
- [x] Add actual CLI smoke/integration checks without downloads/live game starts.
- [x] Update changelog, operator guide, README and developer docs.
- [x] Run focused/full units, smoke and lint10; independent review; update the
  existing separate AlphaGSM PR without merging it.

Verified: 8,965 units passed (4 platform skips), 47 first-run smoke checks,
238 agent smoke checks, 576 focused checks (1 optional skip), full lint10/exit0,
and independent security/docs review. Pushed 02e78efc to existing AlphaGSM PR40;
PR remains open and unmerged. Selector-overwrite red/green reproduced through
the actual CLI; CI runtime-independent test classification is registered.
