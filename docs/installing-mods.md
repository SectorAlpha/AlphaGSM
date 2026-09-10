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
| `workshop` | a numeric Workshop id | Experimental desired-state only; apply is not a supported TF2 install path yet |

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
- Workshop apply for TF2 is still experimental; prefer `manifest`.
- `mod add` without `mod apply` does not install anything yet.
