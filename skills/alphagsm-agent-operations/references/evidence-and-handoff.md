# Evidence and handoff

Report observations separately from inferred causes and proposed actions.
Command exit alone is not game health. Include the real protocol/payload and
expected final state. A missing prerequisite stays a blocker, not a pass.

Use this compact format when execution resumes in another agent/session:

```text
Task: requested operation and approved scope
Target: host / config path / owner / tag / canonical module
Revision/runtime: checkout or binary version; effective backend/image
Before: running state, selected settings and relevant health
Changed: accepted settings, installed content, recovery action
Evidence: command, exit, substantive result, real protocol readiness
Artifacts: absolute paths to redacted logs, selected archive and checksums
After: resulting running state and query/info/shutdown result
Remaining: exact blocker or next authorized step; no secrets
```

Example, with illustrative results that must be replaced by actual evidence:

```text
Task: validate Minecraft Vanilla using disposable data
Target: selected host / /tmp/run/config.conf / current user / evalmc
Revision/runtime: tested commit / process backend / selected Java
Before: no registered evalmc tag
Changed: create, setup and start completed in the scratch install
Evidence: SLP readiness, query/info JSON report protocol slp
Artifacts: /tmp/run/redacted-lifecycle.log
After: stop completed; owned process ended and listener closed
Remaining: none for this validation; no production changes made
```

For fleets, report each target independently, including failures. For backups,
record exact archive identity and coverage/exclusions; file size alone is not
restore proof. For enablement, link the passing lifecycle and tracker changes.
For a PR, include resulting behavior, executed checks and material limitations.
Do not copy raw dump output, secret files, provider tokens or unrelated account
configuration into evidence. A handoff transfers context, not new authorization.
