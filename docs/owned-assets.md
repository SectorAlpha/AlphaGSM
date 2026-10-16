# Import owned game files

Some servers need files from a game you own or files exported by its client.
For modules with an asset recipe, AlphaGSM can arrange those files for you on
Windows and Linux. Project Reclaimer is the first module using this workflow.
Other BYO modules keep their existing documented setup until they adopt a recipe.

Start with a local game folder, prepared server folder, ZIP, or tar archive.
Download or export the files using the game's normal tools first.

```bash
./alphagsm halo create projectreclaimer
./alphagsm halo setup -n 49176 /srv/reclaimer --assets "/srv/uploads/reclaimer.zip"
./alphagsm halo assets check
```

In PowerShell, the same options work with the Windows executable:

```powershell
.\alphagsm.exe halo create projectreclaimer
.\alphagsm.exe halo setup -n 49176 "C:\Servers\Reclaimer" --assets "D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection"
.\alphagsm.exe halo assets check
```

To import after setup, stop the server and run:

```bash
./alphagsm halo assets import "/srv/uploads/owned-game-files"
./alphagsm halo assets check --json
```

AlphaGSM checks required files before copying anything. It imports only the files
declared by that game module. Missing or empty files produce an error explaining
what is needed. A successful asset check confirms file presence, not that the game
can start or that its versions match; the game's own checks still apply.

Imports preserve unrelated files, settings and saves. Unchanged files are skipped.
Files previously installed by the importer can be updated if their installed
contents have not been edited. Differing unowned files and locally modified
imported files cause a conflict; resolve that conflict deliberately before
retrying. Identical existing files are skipped without claiming ownership.

For a Windows-to-Linux transfer, package only the required assets into a ZIP:

```powershell
.\alphagsm.exe halo assets export "D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection" --output "C:\Exports\reclaimer-assets.zip"
```

Run this after `create`; export does not require setup or a running server.
Transfer the ZIP by your usual method, then pass it to Linux's `setup --assets`.
The destination ZIP must be outside the source folder. Exports contain only the
module's selected game files; they do not include AlphaGSM credentials or saves.

Imports and exports reject links, unsafe archive paths, duplicate/colliding
filenames and names that cannot be used on Windows. Keep the source folder
unchanged while importing. Ownership hashes live in `<install_dir>/.alphagsm/assets.json`.

`ENABLED (BYO)` describes a supported module's prerequisites. It does not change
after importing files. `assets check` separately reports whether required files
are present; `doctor` includes the same readiness check. New modules awaiting a
real lifecycle run remain pending validation.
