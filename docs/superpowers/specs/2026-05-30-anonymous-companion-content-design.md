# Anonymous Companion Content Auto-Install Design

Date: 2026-05-30

## Summary

AlphaGSM now has a working `ENABLED (BYO)` support state, but some current BYO
rows are conceptually different from others. A few servers only need
publicly-available companion content or extra anonymous depots staged during
`setup`, similar to how `gmodserver` mounts extra Source content. Others still
need true licensed retail assets that AlphaGSM cannot self-provision. This
design draws that line explicitly and defines how to migrate anonymous-content
lanes out of BYO and back into normal supported installs.

## Goals

- Distinguish `anonymous companion content` from `retail-only assets`.
- Treat anonymous companion content as part of the normal AlphaGSM install
  contract when the content is publicly redistributable or anonymously
  downloadable.
- Keep true retail assets explicit as `ENABLED (BYO)` until a legitimate
  non-BYO install path exists.
- Prefer shared family installers over one-off module hacks.
- Avoid support-state drift where modules stay BYO even though AlphaGSM could
  legally and technically auto-stage their missing content.

## Non-Goals

- Reclassifying proprietary retail assets as auto-installable.
- Inventing unofficial mirrors for licensed game data.
- Converting every BYO server in one pass.
- Changing the meaning of `PASSED`, which still requires a real passing
  integration test.

## Key Distinction

### Anonymous companion content

This content can be fetched or staged automatically as part of `setup` because
it is one of:

- an extra anonymous Steam depot or tool app
- a public redistributable archive
- an upstream companion payload whose license and delivery method already allow
  automated fetching

Example pattern:

- `gmodserver`
  - AlphaGSM installs Garry's Mod itself
  - AlphaGSM also installs extra anonymous Source depots and writes mount
    configuration so those assets are available automatically

These servers should not remain `ENABLED (BYO)` if the only missing piece is
companion content that AlphaGSM can legitimately install.

### Retail-only assets

This content still depends on an owned client install, proprietary retail game
files, account-specific entitlement, or another non-anonymous source that
AlphaGSM cannot self-provision.

Examples:

- `q3server` needing `baseq3/pak0.pk3`
- `cod2server` needing `localized_*.iwd` and `default_localize_mp.cfg`
- `rtcwserver` needing the original multiplayer pk3 set
- current GoldSrc mod payload trees like `ahlserver`, `bbserver`, `nsserver`,
  `tsserver`, and `vsserver`, unless an official anonymous content source is
  later proven

These should stay `ENABLED (BYO)` with exact operator guidance.

## Recommended Classification Rules

Use this decision order for any server currently in `ENABLED (BYO)` or under
support-state review:

1. Can AlphaGSM fetch all missing content anonymously or from a public
   redistributable source?
   - If yes, treat it as normal install content.
2. Is the missing content only a companion payload layered on top of an already
   supported base install?
   - If yes, prefer a shared family installer or shared helper.
3. Does the missing content still require retail ownership, authenticated
   entitlement, or user-generated/exported payloads?
   - If yes, keep `ENABLED (BYO)`.

## Design Approaches

### Approach 1: Keep current BYO behavior

Leave current BYO rows alone and only improve wording when needed.

Pros:

- very low implementation cost
- no risk to existing install paths

Cons:

- leaves auto-installable companion content incorrectly classified
- misses real support improvements for families that could be self-provisioning

### Approach 2: Per-module conversion

Convert each eligible module independently whenever evidence appears.

Pros:

- simple local changes
- low upfront shared design work

Cons:

- duplicates family logic
- encourages drift and inconsistent install behavior
- makes future maintenance harder

### Approach 3: Shared family companion-content installers

Define shared installers for content families, then migrate eligible modules
onto them.

Pros:

- matches how `gmodserver` already behaves
- consistent install/update semantics
- easier to verify and document
- best long-term maintenance path

Cons:

- more initial design work
- requires careful family scoping

### Recommendation

Use Approach 3, but roll it out incrementally. Keep the current BYO rows until
each family-level installer is proven.

## Family-Level Model

### Source-style companion content

Use the `gmodserver` pattern as the baseline:

- install the primary server app
- install extra anonymous depots into a managed content root
- write the server's mount/config metadata automatically
- keep the extra content under AlphaGSM-managed paths inside the install tree

This model is appropriate when the extra content is anonymous and redistributable.

### GoldSrc / mod payload trees

Do not assume current HLDS mod content trees are equivalent to `gmodserver`
without proof. Even though they share an engine family, their current blockers
are complete mod payload trees rather than clearly redistributable anonymous
depots.

Current recommendation:

- keep `ahlserver`, `bbserver`, `nsserver`, `tsserver`, and `vsserver` in
  `ENABLED (BYO)`
- only move them out if an official or otherwise legitimate automated content
  source is found and validated

### Quake / Call of Duty / RTCW retail assets

Keep these as `ENABLED (BYO)` unless a legitimate anonymous redistributable
source exists.

Current examples that should remain BYO:

- `q3server`
- `cod2server`
- `cod4server`
- `coduoserver`
- `rtcwserver`
- `etlegacyserver`

### Java / direct-download server lanes

When a server previously relied on scraping a volatile landing page but still
supports a direct archive URL or staged jar, it belongs in `ENABLED (BYO)` only
until AlphaGSM has a stable automated fetch path again.

Example:

- `minecraft.tekkit`
  - BYO is correct while the Technic page scrape is unreliable
  - if a stable public direct artifact source is later established, this can
    move back to a normal install lane

## Implementation Contract

When converting a server from BYO to auto-installed companion content:

- the companion content must be fetched during `install` / `setup`
- the companion content must be refreshed during `update`
- the module must keep using the shared runtime layer, not hard-coded `screen`
  assumptions
- smoke/integration must reflect the new self-provisioning behavior
- tracker/docs must move the module out of `ENABLED (BYO)` only after the real
  lifecycle passes

When keeping a server in BYO:

- `setup` and/or `start` must fail fast with an explicit BYO requirement
- guides must explain the exact staged files, paths, tokens, or export steps
- tracker wording must match the actual technical blocker

## Migration Plan

1. Audit current `ENABLED (BYO)` rows into:
   - anonymous companion content candidates
   - retail-only asset lanes
   - auth/export/config lanes that stay BYO
2. Add or extend shared family installers for the anonymous companion-content
   candidates.
3. Prove those lanes with smoke and integration.
4. Move only the proven lanes from `ENABLED (BYO)` to normal supported status.
5. Leave retail-only lanes in BYO with exact operator guidance.

## Initial Candidate Guidance

Likely keep as BYO for now:

- `ahlserver`
- `bbserver`
- `nsserver`
- `tsserver`
- `vsserver`
- `cod2server`
- `cod4server`
- `coduoserver`
- `q3server`
- `rtcwserver`
- `etlegacyserver`

Good candidates for future anonymous companion-content investigation:

- server families that resemble `gmodserver` by depending on extra anonymous
  depots or public redistributable companion payloads rather than retail game
  files
- current examples worth rechecking first:
  - `zmrserver`
  - any Source-family module whose blocker is "incomplete anonymous mod payload"
    rather than owned assets

## Testing and Verification

For any family conversion:

- add or update focused unit tests for the new installer behavior
- prove that `install` and `update` both stage the companion content
- keep smoke/integration aligned with the new contract
- regenerate and check `docs/game-server-support.md`

For any server kept in BYO:

- verify the fail-fast message is exact
- verify docs, smoke headers, and integration skip reasons all match

## Resolved Decision

`gmodserver` is the right model only for anonymous companion content, not for
retail-only base-game assets. AlphaGSM should auto-install what it can
legitimately fetch, and keep explicit BYO handling for the rest.
