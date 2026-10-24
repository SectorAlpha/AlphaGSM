# Hostname publication preflight

User clarified existing DNS only: a hostname/subdomain such as
game.mygameserver.com must resolve to the machine running AlphaGSM before the
agent advertises it to sector-alpha.net. No DNS registration/provider is needed.

- Gate public hostname snapshots immediately before report POST. Only failed
  binding publication becomes false in the copied outgoing snapshot; stored
  permissions, metadata and consent remain unchanged. Private/numeric hosts keep
  existing behavior. Other bindings keep reporting.
- Support repeatable local-only --public-ip overrides (expected_public_ips field
  outside metadata/wire contracts); validate global unicast addresses, normalize
  and preserve on rerun. Without overrides use allowlisted local networking
  hints, routing/IP discovery once per batch. Require every complete bounded
  A/AAAA answer to be global and match an expected machine IP.
- DNS checks are bounded and repeated on renewals. No DNS timeout may continue to
  a later connection. Native endpoint checks use only fixed profile protocols,
  pinned matched addresses and original SLP virtual host, never private targets.
  Keep aggregate preflight work bounded and ensure failures on early bindings
  cannot permanently starve later healthy hostname bindings.
- Failures explain DNS mismatch, unavailable public-IP detection, unsupported
  address family, or public endpoint failure without disclosing credentials.
  Existing endpoint ownership challenge and central SSRF policies remain intact.
- Red/green tests cover full-answer rejection, IPv4/IPv6, overrides/defaults,
  timeout/no-late-probe, DNS change/repair, no wire leakage, per-binding isolation,
  backward-compatible config/idempotent reruns, cache/fairness if needed, and
  bounded real protocol fixtures. Update operator/technical docs and changelog.
- Review spec and security independently; run offline/full unit/lint and affected
  real Minecraft plus portal HTTPS journey before updating AlphaGSM PR40.

Completed and independently reviewed. Final commit 76bd02ba is pushed to PR #40
(open against master). Fresh complete unit run: 8,857 passed, 4 existing skips;
full lint: 10.00/10, 35 skills validated. Offline agent gate: 164 passed. Real
frozen Linux Minecraft lifecycle/binding/restart/duplicate integration passed;
the final binary was rebuilt after the Python 3.12 HTTPS compatibility repair.
Final three portal client TLS journeys passed together, including DNS withdrawal,
repair and consent mutation during lookup. Shared exported protocol files remain
identical to the service's pinned 0f8b04fe revision. No live demo state modified.
