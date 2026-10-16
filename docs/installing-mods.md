# Installing Mods

AlphaGSM can install **server-side** mods, plugins, and addons for some games.
It does not install client-only or single-player content.

The everyday flow is always:

```bash
alphagsm <name> mod add <source> <id>
alphagsm <name> mod apply
```

`mod add` records what you want. `mod apply` downloads it into the server tree
and remembers which files AlphaGSM owns. `mod list` shows that desired state.
`mod cleanup` removes only those owned files.

## Team Fortress 2 (worked example)

Create and set up the server first. Mods install into the dedicated-server
tree, so they need a completed `setup`.

```bash
alphagsm mytf2 create teamfortress2
alphagsm mytf2 setup
```

Install MetaMod and SourceMod from AlphaGSM's checked-in list:

```bash
alphagsm mytf2 mod add manifest metamod
alphagsm mytf2 mod add manifest sourcemod
alphagsm mytf2 mod apply
alphagsm mytf2 mod list
```

Those families land under `tf/addons/` and `tf/cfg/`. You can pin a SourceMod
channel when the registry exposes one:

```bash
alphagsm mytf2 mod add manifest sourcemod 1.12
alphagsm mytf2 mod apply
```

`manifest` is the supported path. `curated` is still accepted as the same
command. The TF2 smoke runner uses this same add-then-apply order.

### Other TF2 sources

| Source | You provide | Use when |
| --- | --- | --- |
| `manifest` | a family name (`sourcemod`, `metamod`, `prophunt`) | You want AlphaGSM's known, reproducible entry |
| `gamebanana` | a numeric item id | The addon is hosted on GameBanana |
| `moddb` | a Mod DB download or addon page URL | The file is a supported zip/tar archive |
| `workshop` | a Workshop item id or official URL | You want a multiplayer map loaded by TF2's native Workshop loader |
| `workshop-collection` | a collection id or official URL | You want all validated multiplayer maps in a collection |

```bash
alphagsm mytf2 mod add gamebanana 12345
alphagsm mytf2 mod add moddb https://www.moddb.com/mods/cage-eight/downloads/cage-eight
alphagsm mytf2 mod apply
```

Remove AlphaGSM-tracked addon files:

```bash
alphagsm mytf2 mod cleanup
```

Cleanup does not delete the rest of the TF2 install.

### Custom maps

TF2 custom maps use the same desired-state idea:

```bash
alphagsm mytf2 map add curated cp_granary_pro_rc8
alphagsm mytf2 map apply
alphagsm mytf2 map list
```

Checked-in map families currently include competitive maps such as
`cp_granary_pro_rc8`, `koth_product_rcx`, and `pl_vigil_rc10`. Files land under
`tf/maps/`.

## Same commands on other games

### Steam Workshop items and collections

L4D2, Garry's Mod, Unturned, Project Zomboid, CS2 and TF2 accept `workshop` items and `workshop-collection`
collections using either numeric IDs or Steam Community Workshop URLs.
AlphaGSM checks Steam's game AppID for the item or collection
and every nested child before saving anything. Unavailable, private, wrong-game,
empty, and cyclic collections are rejected. When Steam does not return an id,
the command says it was not found and that it may be private, unlisted, or
removed. A found item or collection prints its visibility, including public,
and its title when Steam provides one. A same-game check does not prove
that an addon works on a dedicated server; the module also checks its payload.

```bash
alphagsm myl4d2 mod add workshop ITEM_ID
alphagsm myl4d2 mod add workshop-collection COLLECTION_ID
alphagsm myl4d2 mod add workshop "https://steamcommunity.com/sharedfiles/filedetails/?id=762591677"
alphagsm myl4d2 mod list
alphagsm myl4d2 mod apply
```

Replace the uppercase placeholders with numeric Steam IDs or Workshop URLs. Collections are
snapshots: importing again adds newly listed items and skips duplicates, while
keeping previously requested items. To remove one item, run
`alphagsm myl4d2 mod remove workshop ITEM_ID`, then `mod apply`.

SteamCMD uses `login anonymous` on these modules. Some games/items require an
entitled Steam account; AlphaGSM reports the download failure if anonymous
access is denied. Public visibility does not guarantee anonymous download access.

Every game-server module that installs through anonymous SteamCMD also exposes
the shared download command, including modules without automatic mod installation:

```bash
alphagsm myserver workshop download item ITEM_ID_OR_URL
alphagsm myserver workshop download collection COLLECTION_ID_OR_URL
alphagsm myserver workshop list
```

Run server `setup` first. AlphaGSM checks the module's declared Workshop game
AppID, the configured Source game's `gameinfo.txt`, or the game AppID in the
upstream installation's `steam_appid.txt`,
before downloading anything. Missing or conflicting identity fails with an
explanation; the server-tool AppID is not used as a substitute. Private,
unavailable, or wrong-game content also fails before any download starts.

Downloads are staged under the server directory at
`.alphagsm/workshop/content/<game-appid>/<item-id>/`; the command prints each
location and `workshop list` records completed downloads. Downloading an item
again replaces its staged payload, including files removed by the upstream update.
Use the game's own
mod installation and configuration rules to activate this content. Downloading
does not establish that a mod loads on the server. Anonymous server installation
does not guarantee that its publisher permits anonymous Workshop downloads.

L4D2 accepts one bare `.vpk` per Workshop item and installs it under
`left4dead2/addons/workshop/<item-id>.vpk`. It applies enabled desired addons
before starting. CS2 retains its addon/config-tree installer; it does not
automatically install arbitrary Workshop map packages. TF2 uses native map sync
commands; after apply, select a map with `set map workshop/ITEM_ID`. Cosmetic
uploads are rejected. Its process load test passed; Docker validation is pending.

The native loaders use the same commands but activate content according to the game:

| Server | Workshop game AppID | Activation |
| --- | --- | --- |
| Garry's Mod | `4000` | Validated GMA contents extracted into owned addon directories |
| Unturned | `304930` | Owned IDs in `WorkshopDownloadConfig.json`; select the installed map with the native `Map` command in `Commands.dat` |
| Project Zomboid | `108600` | Download and inspect `mod.info`, then maintain `WorkshopItems` and `Mods` in the server profile |
| Barotrauma | `602960` | Validate the content package and enable its native package entry |
| Avorion | `445220` | Validate Lua mod metadata and add owned declarations to `modconfig.lua` |
| Insurgency / Day of Infamy | `222880` / `447820` | Maintain owned `subscribed_file_ids.txt` entries and enable native Workshop map loading |
| No More Room in Hell | `224260` | Validate map assets and stage them in native game content directories |
| BrainBread 2 | `346330` | Validate map assets and use the game's existing per-item Workshop search path |
| Conan Exiles | `440900` | Stage owned PAK files and ordered `modlist.txt` entries |
| Terraria tModLoader | `1281930` | Validate compatible `.tmod` packages and preserve operator entries in `Mods/enabled.json` |

The [Workshop support matrix](WORKSHOP_SUPPORT.md) records actual engine-load
evidence, separately for process and Docker, including current blockers.
Anonymous download success alone is insufficient to mark a native loader passed.

These adapters preserve existing operator configuration. Their `mod list` reports
configured desired state; the live tests require engine evidence before claiming
that content loaded. Use `mod remove workshop ID_OR_URL`, then `mod apply` to
remove an owned entry. For Unturned and Project Zomboid, `mod cleanup`
clears managed native declarations and desired entries, retaining download caches.
Source addon cleanup removes tracked files, clears desired entries, and removes
its addon cache. See each server guide for payload restrictions and runtime
prerequisites.

The L4D2 Workshop integration test checks Back To School collection `121115793`
and the independent Admin System item `214630948` by default,
with process and Docker lifecycles. It requires every installed VPK to appear
in the running engine's `show_addon_load_order` output. This proves mounting; addon-specific
gameplay effects can still need a client or custom-map test. See the
[L4D2 guide](servers/l4d2server.md) for how to run it.

HL2DM, Garry's Mod, Left 4 Dead 2, and other Source wrappers use the same
`mod add` / `mod apply` / `mod cleanup` surface. Their checked-in `manifest`
families usually include `metamod` and `sourcemod`. Garry's Mod also has
`ulib`, `ulx`, and `advdupe2`; adding `ulx` installs `ulib` automatically.

```bash
alphagsm myhl2dm mod add manifest metamod
alphagsm myhl2dm mod add manifest sourcemod
alphagsm myhl2dm mod apply
```

Paper, the Minecraft proxies, and TShock use the same actions for **plugins**
(`viaversion`, `luckperms`, `essentialsx`, and so on). See the matching server
guide for the family names.

Not every game has a `mod` command. Palworld, for example, has no AlphaGSM mod
installer today.

## What AlphaGSM will not do

- It will not fetch client-only or single-player mods.
- It will not write files outside the approved addon/plugin directories.
- TF2 Workshop activation accepts multiplayer maps, with map-mode metadata.
- `mod add` without `mod apply` does not install anything yet.
