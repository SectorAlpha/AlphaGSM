# Guided Sector Alpha enrollment and binding

Use the existing isolated `codex/sector-alpha-agent` branch and update PR #40.
Default enrollment to `https://sector-alpha.net`; allow `enroll --origin URL`
for other compatible providers. Ask only for the hidden enrollment code. Accept
and normalize a root trailing slash, while continuing to reject HTTP, credentials,
paths, query strings, fragments and credential redirects.

`alphagsm agent setup` and `alphagsm agent bind '*'` discover and bind all managed
local game servers; `bind my-minecraft` selects one. Setup enrolls first when
needed, using a hidden website enrollment code. A scoped authenticated endpoint
registers central bindings automatically; no copied binding IDs are needed.
Default epoch to 1, infer the game/module, query/game port, display
name and capacity from an allowlisted snapshot of local datastore fields, then
show suggested public address/port with overrides. Do not call game queries,
console/RCON or copy private datastore fields into reports.

Public address discovery prefers a configured global publicip/externalip/hostip,
then a global address from outbound routing, then a fixed verified-TLS ipify IPv4
lookup. Reject invalid/non-global lookup responses, redirects and oversized data;
bound requests and never include enrollment/agent credentials. `--host` skips
lookup entirely; `--port` overrides the inferred endpoint for NAT/port forwarding.
When detection fails, prompt for an address or reject cleanly in unattended use.
Detection is a suggestion, not endpoint verification. VPN, NAT and IPv6-only setups
may need an override; central endpoint challenge remains authoritative.

Guided setup shows the complete discovered server list and asks whether to publish
supported public profiles (default no), and which remote actions to
allow (default none; explicit status or all four operations). Show the completed
allowlisted settings for confirmation before the atomic binding write. Cancellation
and failed validation leave the previous binding/policy unchanged. Enrollment
and binding do not enable global capabilities or start a background service.
Print short relevant next steps. Never offer a capability not enrolled.

Retain the legacy two-positional `bind BINDING_ID SERVER` form, existing explicit
flags, and script compatibility. Make game/port/name/capacity optional by inference;
retain explicit overrides and game-match checking. Add `--binding-id` for a
short-form override and `--private` to explicitly opt out of publication. Legacy
fully supplied invocations remain noninteractive and preserve their permission
defaults. Invalid/missing scripted input returns a safe error instead of hanging.

Private reporting/management bindings support all existing canonical local modules.
Publication/player queries stay restricted to the reviewed Minecraft/TF2 profiles.
Servers lacking a configured valid port or unreadable/invalid datastore are shown
as unavailable for binding, with an actionable reason; never pretend they were bound.
Exclude secret sidecars/symlinks and cross-user selectors. Avoid duplicate local
tags, existing-binding permission changes and unnecessary policy increments on
reruns. Cap one installation at 100 local bindings and report partial failures.

## Scoped backend registration

POST `/v1/agent/bindings` accepts exactly `{scope, binding_ref}`. Scope is reporting
or management; binding_ref is a 64-character lowercase SHA-256 of the local tag.
Authenticate the selected capability and derive the installation/owner from its
key, never the request. Registration requires an active verified MFA owner, and
management scope also requires the existing management switch. Return exactly
`{schema_version: 1, binding_id, binding_epoch}`.

Derive an idempotent binding ID as `agent-` plus the existing digest of
`installation_id + ':' + binding_ref`. Existing bindings are returned unchanged;
new ones have epoch 1, empty actions and no metadata/public listing. Enforce a
100-active-binding limit and durable new-binding quota under the shared security
transaction; retries and races must allocate only once and preserve scope/isolation.
No schema migration or raw local tag storage is required. Central private reports
accept canonical unsupported games without creating public query/listing state;
unsupported publication still fails closed. Revocation, MFA reset and disabled
accounts prevent new registration.

Test default/alternate origins, slash normalization and secret prompts; guided
accept/cancel/invalid/rebind paths; supported metadata inference and game mismatch;
discovery routing/NAT/failure/oversize/non-global/TLS/redirect behavior; override
precedence/no network on --host; no secret serialization; legacy CLI compatibility.
Use real Config and an isolated local server, plus the existing integration test
to exercise inferred binding on a real temporary Minecraft server. Run full units,
offline gate, lint, integration, and independent review before pushing PR updates.
