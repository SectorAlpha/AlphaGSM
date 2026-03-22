# Manual Download Fallbacks

This file is for game server modules that require a user-supplied `--url` during `setup`.

These modules do not currently have a built-in official download resolver inside AlphaGSM. To make
them usable anyway, this guide documents the archive shape AlphaGSM expects and the kind of source
URL you should look for.

## How To Use This

When a module asks for `--url`, look for a direct download URL that:

1. downloads the archive type shown below
2. roughly matches the filename pattern shown below
3. extracts the expected executable shown below

If the exact filename changes between releases, that is fine. The important part is that the
archive contains the expected server executable or launcher.

## Manual URL Modules

| Module id | Expected archive | Expected executable | Fallback source or URL shape |
| --- | --- | --- | --- |
| `hogwarpserver` | `hogwarp-server.zip` | `HogWarpServer.exe` | HogWarp server files are distributed inside the Nexus Mods release for the project. Start from `https://www.nexusmods.com/hogwartslegacy/mods/1378` and the official docs at `https://docs.hogwarp.com/`, which state the server is included in the release under the `Server` folder. |
| `mxbikesserver` | `mxbikes-dedicated.zip` | `mxbikes_dedicated` | MX Bikes does not currently expose a clean public dedicated-server archive feed. Use the official game distribution from Steam (`https://store.steampowered.com/app/655500/MX_Bikes/`) or PiBoSo references, and the dedicated-server docs at `https://wiki.mxb-mods.com/dedicated-server/` / `https://docs.piboso.com/wiki/index.php?title=Dedicated_Server`. |

## Notes

| Topic | Note |
| --- | --- |
| Direct archive URL | The value passed to `--url` should point straight at the downloadable archive, not a landing page. |
| Filename mismatch | The exact release filename can change. AlphaGSM mostly cares that the archive extracts the expected executable. |
| Manual modules | These modules are good candidates for future built-in resolvers if a stable official API or release pattern becomes available. |
| Still manual | The remaining entries do not have a stable anonymous direct-download archive AlphaGSM can safely depend on. HogWarp is distributed through Nexus release packaging, and MX Bikes is documented as a dedicated-server flow from the main game installation rather than a clean standalone server archive feed. |
