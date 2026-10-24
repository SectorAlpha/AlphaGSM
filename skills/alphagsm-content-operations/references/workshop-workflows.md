# Workshop downloads and native activation

Use this when the selected checkout exposes Workshop support. Inspect server
help, module hooks and the matching [content guide](../../../docs/installing-mods.md)
first. Earlier versions may expose only desired state or curated addons. Do not
infer capability from the game name or from an incoming PR.

On Workshop-capable checkouts, read `docs/WORKSHOP_SUPPORT.md` if present for
per-game anonymous access and separate process/Docker native-load evidence.
Keep pending/blocked rows pending; a stock server pass is not a Workshop pass.
Use current hooks and canonical smoke/integration checks when prose disagrees.

## Choose the supported operation

| Surface in the selected module | Meaning | Completion evidence |
| --- | --- | --- |
| `workshop download item/collection`, `workshop list` | Shared anonymous staging, possibly without a native mod adapter | Verified item-specific payload and reported staged location; activation remains separate |
| `mod add workshop/workshop-collection`, `mod apply` | Desired state plus module-specific payload/config activation | Fresh native mount/map/registry/mod execution evidence plus actual server health |
| Curated/manifest addons or plugins only | Existing supported provider/installer | Use its actual add/apply path; do not invent generic Workshop activation |

After the requested server setup, the shared download lane is:

```bash
alphagsm myserver workshop download item "$WORKSHOP_ITEM_ID_OR_URL"
alphagsm myserver workshop download collection "$WORKSHOP_COLLECTION_ID_OR_URL"
alphagsm myserver workshop list
```

Use only if help advertises it. It is a download operation, not a replacement
for `mod apply`. Payloads are staged under
`.alphagsm/workshop/content/<game-appid>/<item-id>/`; repeated downloads replace
that item's staged payload. Follow the game's supported activation path.
Never invent `workshop apply` or `workshop cleanup`.
If a collection download fails after some items complete, inspect `workshop list`
and report those completed IDs plus the error. Metadata validation does not make
the multi-item download atomic; do not claim all items failed or all succeeded.

IDs and official Steam Community file-details URLs can identify items and
collections. The installed helper validates the actual consumer game AppID
and every nested collection member before import/download. A dedicated-server
tool AppID is not a substitute. Missing/conflicting identity, wrong-game,
unavailable/private content and unsupported payloads are real errors, not
approval gates to bypass. A public item or an anonymous game install does not
guarantee anonymous Workshop access. Report denial; do not introduce an account,
API key or provider token path that the module does not support.

Native desired-state collection import is a snapshot: reimport adds new validated
members, skips duplicates and retains prior requests. It does not continuously
subscribe or silently remove items. Inspect the resulting desired list and
explicit scope. The generic collection downloader instead stages downloads; it
does not create native desired subscriptions.

## Native loaders

When a module supports native Workshop activation, inspect its adapter and game
guide; each engine has different payload/configuration rules. For an installed
TF2 with the native map adapter, the supported sequence includes:

```bash
alphagsm mytf2 mod add workshop "$WORKSHOP_ITEM_ID_OR_URL"
alphagsm mytf2 mod apply
alphagsm mytf2 set map "workshop/$WORKSHOP_ITEM_ID"
alphagsm mytf2 start
```

Use the normalized numeric item ID for the map value. TF2's adapter validates
multiplayer-map metadata and configures native synchronization; cosmetic uploads
are not maps. Verify a fresh native map load and real A2S map identity.
Do not infer Docker load validation from a process result.

For `terraria.tmodloader` when available, use its public GitHub release installer
and matching server-compatible mod packages. Inspect release/package compatibility,
Both/Server support and declared dependencies; add required mods through the
supported workflow without extra approval questions. The native launcher may
acquire its .NET runtime on first startup inside the managed installation.
Use the module's documented `start --autocreate` only for the intended missing
world. Native Terraria readiness and a fresh mod command/execution result prove
more than an enabled JSON entry. Do not require Steam-client login for this
public-release install, or substitute the TShock runtime/install recipe.

## Ownership, cleanup and reporting

Preserve unowned files/config entries. Native adapters can transactionally track
payload hashes and reject externally edited managed files; do not delete those
files to make apply/cleanup succeed. Retained backups/recovery manifests from a
failed rollback are recovery evidence, not disposable caches.

Use per-item `mod remove workshop ITEM_ID` followed by apply where advertised.
`mod cleanup` can remove the full managed set. Native cleanup may remove owned
configuration while retaining engine-generated content and download caches;
those retained files do not by themselves mean a mod is still active. If
deactivation is requested, verify it through a fresh restart and native state
when required by the adapter, within the intended server-state scope.

Report requested, downloaded, staged/configured and natively loaded states
separately. Fresh logs, registry/mount responses or mod execution must come from
the current lifecycle; cached files, old snapshots and config echoes cannot
establish load. A forced stop/closed port is shutdown evidence, not proof of a
graceful world save.
