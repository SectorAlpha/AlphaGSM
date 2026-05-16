# AlphaGSM

AlphaGSM helps you run game servers.

You do not need to be deeply technical to use it. If you can copy and paste commands into a terminal, that is enough for most single-server setups.

AlphaGSM can:

- download server files
- set a server up
- start it
- stop it
- update it
- back it up

It can run directly on the host, or optionally run as a Docker "manager"
container that launches Docker-backed game-server containers through the host
daemon.

It can also run directly on the host while still using Docker as the runtime for
individual game servers.

If you want the Docker-manager route, there is also a root wrapper script:

For many first-time setups, this is the quickest way to get started because it
avoids most of the host-side Python, Java, and system-package setup.

```bash
./alphagsm-docker start
./alphagsm-docker mymc create minecraft.vanilla
./alphagsm-docker ps
./alphagsm-docker mymc connect
```

The wrapper keeps runtime-image pre-pull off by default so it works without
GHCR login for a first run. By default it tries to pull the latest manager
image from GHCR and falls back to a local build if that pull fails. If you are
working on AlphaGSM itself, `./alphagsm-docker start --develop` switches the
wrapper into a local-build developer mode.
`./alphagsm-docker ps` reads local wrapper metadata and expects a working host
`python3`. For Docker-backed servers, `./alphagsm-docker <server> connect`
uses that local metadata when it can, and otherwise falls back to AlphaGSM's
normal forwarded `connect` command.

See [Run AlphaGSM In Docker](docs/docker-manager.md).

If you want a quick server-by-server support checklist, see
[Game Server Support Tracker](docs/game-server-support.md).

## What You Need

You need:

- Python 3
- `screen`
- the Python packages in `requirements.txt`

`gmodserver` note: setup also downloads common mountable Source content into a separate `_gmod_content/` directory and writes `garrysmod/cfg/mount.cfg` plus `mountdepots.txt` defaults.

Some server types need one extra thing:

- Minecraft needs Java:
  ```bash
  sudo apt install openjdk-25-jre-headless
  ```
- TF2, CS:GO, and other Steam-based servers need 32-bit runtime libraries:
  ```bash
  sudo dpkg --add-architecture i386
  sudo apt update
  sudo apt install lib32gcc-s1 lib32stdc++6
  ```
- Some servers distribute archives in 7z format:
  ```bash
  sudo apt install p7zip-full
  ```
- A few older native Linux servers still need legacy compatibility packages
  that Ubuntu 24.04 no longer ships in its normal repos. `atlasserver`
  currently needs `libprotobuf.so.10`, `libidn.so.11`, and `liblber-2.4.so.2`,
  which you can install with:
  ```bash
  wget http://archive.ubuntu.com/ubuntu/pool/main/p/protobuf/libprotobuf10_3.0.0-9.1ubuntu1_amd64.deb
  wget http://archive.ubuntu.com/ubuntu/pool/main/libi/libidn/libidn11_1.33-2.2ubuntu2_amd64.deb
  wget http://archive.ubuntu.com/ubuntu/pool/main/o/openldap/libldap-2.4-2_2.4.49+dfsg-2ubuntu1.10_amd64.deb
  sudo apt install ./libidn11_1.33-2.2ubuntu2_amd64.deb
  sudo apt install ./libldap-2.4-2_2.4.49+dfsg-2ubuntu1.10_amd64.deb
  sudo apt install ./libprotobuf10_3.0.0-9.1ubuntu1_amd64.deb
  ```
- Some native Linux servers also expect the unversioned LLVM C++ loader name
  `libc++.so`. `pvrserver` currently needs `libc++1` plus a compatibility
  symlink to the real `libc++.so.1` shared object:
  ```bash
  sudo apt install libc++1
  sudo ln -sf /lib/x86_64-linux-gnu/libc++.so.1 /lib/x86_64-linux-gnu/libc++.so
  ```

## Fast Start

If you want the quickest first run, start with the Docker-manager path above.
The host install below is still the right option when you want AlphaGSM running
directly on the machine instead of through Docker.

If you want AlphaGSM on the host but want supported game servers to start as
Docker containers, see [Run Docker-Backed Servers From Host AlphaGSM](docs/docker-runtime-host.md).

### 1. Install the Python packages

```bash
pip install -r requirements.txt
```

### 2. Make your config file

```bash
cp alphagsm.conf-template alphagsm.conf
```

For most people, the default config is fine to start with.

### 3. Create a server

Minecraft:

```bash
./alphagsm mymc create minecraft.vanilla
```

Team Fortress 2:

```bash
./alphagsm mytf2 create teamfortress2
```

TF2 also exposes canonical `set` aliases and discovery:

```bash
./alphagsm mytf2 set --list
./alphagsm mytf2 set gamemap --describe
./alphagsm mytf2 set gamemap cp_dustbowl
./alphagsm mytf2 set rconpassword secret
```

Counter-Strike 2:

```bash
./alphagsm mycs2 create counterstrike2
```

### 4. Run setup

```bash
./alphagsm mymc setup
```

Setup may ask for:

- a port number
- where the files should be installed
- which version to download
- where Java is installed for Minecraft

### 5. Start the server

```bash
./alphagsm mymc start
```

### 6. Check that it is running

```bash
./alphagsm mymc status
```

If you configured `[runtime] backend = docker`, use the runtime doctor command
before `start` when you want to confirm which backend, image, and container
state AlphaGSM will use:

```bash
./alphagsm mymc doctor
```

### 7. Stop it later

```bash
./alphagsm mymc stop
```

## Commands You Will Probably Use Often

Send a message:

```bash
./alphagsm mymc message "Server restarting soon"
```

Back the server up:

```bash
./alphagsm mymc backup
```

Update a Steam game server:

```bash
./alphagsm mytf2 update
./alphagsm mytf2 update -r
```

TF2 mod sources are split into AlphaGSM-owned manifest entries and external
provider ids:

- `manifest` uses AlphaGSM's known mod registry. This is the supported,
  reproducible path for entries such as SourceMod and MetaMod.
- `gamebanana` and `workshop` use a provider item id that AlphaGSM resolves
  live from that external service.
- `moddb` uses a canonical Mod DB download or addon page URL that AlphaGSM
  resolves to Mod DB's own start-download link when the file is a supported
  zip or tar archive.
- GameBanana, Mod DB, and Steam Workshop are universal provider types rather
  than TF2-only catalogs. TF2 is just one module using them here.
- `curated` is still accepted as a compatibility alias for `manifest`.

Examples:

```bash
./alphagsm mytf2 mod add manifest sourcemod
./alphagsm mytf2 mod add gamebanana 12345
./alphagsm mytf2 mod add moddb https://www.moddb.com/mods/cage-eight/downloads/cage-eight
./alphagsm mytf2 mod add workshop 1234567890
./alphagsm mytf2 mod apply
./alphagsm mytf2 mod cleanup
```

CS2 also exposes provider-based server-side mod management for `gamebanana`,
`moddb`, and `workshop` sources:

```bash
./alphagsm mycs2 mod add gamebanana 12345
./alphagsm mycs2 mod add moddb https://www.moddb.com/mods/cage-eight/downloads/cage-eight
./alphagsm mycs2 mod add workshop 1234567890
./alphagsm mycs2 mod apply
./alphagsm mycs2 mod cleanup
```

Paper exposes plugin management with a variant-specific cache root so
Minecraft variants stay separate, with a checked-in `manifest` for reproducible
plugin families such as `viaversion`, `viabackwards`, `viarewind`,
`luckperms`, `vault`, `placeholderapi`, `protocollib`, `essentialsx`,
`essentialsxchat`, `essentialsxspawn`, `essentialsxprotect`,
`essentialsxantibuild`, and `discordsrv`, direct `url` support for single
jars, and `moddb` support for provider-hosted archives:

```bash
./alphagsm mypaper mod add manifest viaversion
./alphagsm mypaper mod add manifest viabackwards
./alphagsm mypaper mod add manifest viarewind
./alphagsm mypaper mod add manifest luckperms
./alphagsm mypaper mod add manifest essentialsxchat
./alphagsm mypaper mod add url https://plugins.example.invalid/TestPlugin.jar
./alphagsm mypaper mod add moddb https://www.moddb.com/mods/paper-plugin-pack/downloads/paper-plugin-pack
./alphagsm mypaper mod apply
./alphagsm mypaper mod cleanup
```

`viabackwards` layers on top of `viaversion`, and `viarewind` layers on top of
both. `essentialsxchat` layers on top of `essentialsx`. AlphaGSM now installs
those prerequisites automatically for the checked-in Paper manifest entries.

BungeeCord, Velocity, and Waterfall now expose the same plugin-management flow,
with checked-in proxy-aware `manifest` registries for reproducible proxy-plugin
families such as `viaversion`, `viabackwards`, `viarewind`, `luckperms`, and
`geyser`, direct `url` support for single jars, `moddb` support for
provider-hosted archives, and a separate
`.alphagsm/mods/minecraft-<variant>/` cache/state root for each proxy variant:

```bash
./alphagsm myproxy mod add manifest viaversion
./alphagsm myproxy mod add manifest viabackwards
./alphagsm myproxy mod add manifest viarewind
./alphagsm myproxy mod add manifest luckperms
./alphagsm myproxy mod add manifest geyser
./alphagsm myproxy mod add url https://plugins.example.invalid/TestPlugin.jar
./alphagsm myproxy mod add moddb https://www.moddb.com/mods/proxy-pack/downloads/proxy-pack
./alphagsm myproxy mod apply
./alphagsm myproxy mod cleanup
```

`viabackwards` layers on top of `viaversion`, and `viarewind` layers on top of
both. AlphaGSM now installs those prerequisites automatically for the checked-in
proxy manifest entries, and it selects the matching Bungee-compatible or
Velocity-compatible jar automatically for families like `luckperms` and
`geyser`.

Use that flow with `minecraft.bungeecord`, `minecraft.velocity`, or
`minecraft.waterfall`.

TShock also keeps plugin cache/state isolated under its own variant-specific
directory:

```bash
./alphagsm mytshock mod add manifest banguard
./alphagsm mytshock mod add manifest smartregions
./alphagsm mytshock mod add manifest perplayerloot
./alphagsm mytshock mod add url https://plugins.example.invalid/ExamplePlugin.dll
./alphagsm mytshock mod add moddb https://www.moddb.com/mods/example/downloads/example-plugin-pack
./alphagsm mytshock mod apply
./alphagsm mytshock mod cleanup
```

The built-in TShock manifest currently seeds a few common plugin families with
checked-in release URLs, including `banguard`, `smartregions`, `omni`,
`perplayerloot`, `autoteam`, and `facommands`.

Popular Source games now expose the same desired-state flow for server-side
addons. Garry's Mod accepts direct `.gma` URLs plus GameBanana and Mod DB
archive installs, while Left 4 Dead 2 accepts direct `.vpk` URLs plus the same
archive providers. Both now also accept checked-in `manifest` entries for
popular admin/plugin stacks such as MetaMod and SourceMod, while Garry's Mod
also carries checked-in `ulib`, `ulx`, and `advdupe2` families and can install
bare addon-root archives into `garrysmod/addons/<family-or-archive-name>/`.
Adding `ulx` now also installs its checked-in `ulib` dependency
automatically, and checked-in GMod manifest entries can install single-file
`.gma` assets such as AdvDupe2. Both keep owned-file cleanup under separate
cache roots:

```bash
./alphagsm mygmod mod add manifest metamod
./alphagsm mygmod mod add manifest sourcemod
./alphagsm mygmod mod add manifest ulib
./alphagsm mygmod mod add manifest ulx
./alphagsm mygmod mod add manifest advdupe2
./alphagsm mygmod mod add url https://addons.example.invalid/example-addon.gma
./alphagsm mygmod mod add gamebanana 12345
./alphagsm mygmod mod add moddb https://www.moddb.com/mods/example/downloads/example-addon-pack
./alphagsm mygmod mod apply
./alphagsm myl4d2 mod add manifest metamod
./alphagsm myl4d2 mod add manifest sourcemod
./alphagsm myl4d2 mod add url https://mods.example.invalid/custom-campaign.vpk
./alphagsm myl4d2 mod add gamebanana 12345
./alphagsm myl4d2 mod add moddb https://www.moddb.com/mods/example/downloads/example-addon-pack
./alphagsm myl4d2 mod apply
```

The same shared addon flow now also covers `insserver` and `hl2dmserver`, using
`manifest`, direct archive URLs, `gamebanana`, and `moddb` sources for payloads
that install under `insurgency/addons/` or `hl2mp/addons/`.

The same flow now also covers the remaining thin Source wrappers with standard
`addons/` layouts, including `ahl2server`, `bb2server`, `bmdmserver`,
`bsserver`, `ccserver`, `cssserver`, `dabserver`, `doiserver`, `dodsserver`,
`dysserver`, `emserver`, `fofserver`, `hldmsserver`, `iosserver`, `l4dserver`,
`ndserver`, `nmrihserver`, `pvkiiserver`, `sfcserver`, `zmrserver`, and
`zpsserver`. Their built-in shared Source manifest currently exposes the
`metamod` and `sourcemod` admin/plugin families.

Show help:

```bash
./alphagsm --help
```

Check whether AlphaGSM itself has an update available:

```bash
./alphagsm self-update --check
```

Apply a self-update when running from a tracked stable git branch or a
standalone release binary:

```bash
./alphagsm self-update
```

## The Best Real Examples

If you want examples that show the exact order of commands that work in this repository, use the smoke-test scripts:

```bash
bash ./tests/smoke_tests/run_minecraft_vanilla.sh
bash ./tests/smoke_tests/run_tf2.sh
```

These scripts are useful because they show a full real flow:

1. create the server
2. run setup
3. start it
4. check it
5. stop it cleanly

## Step-By-Step Server Guides

- [Documentation Index](docs/README.md)
- [Run Docker-Backed Servers From Host AlphaGSM](docs/docker-runtime-host.md)
- [Run AlphaGSM In Docker](docs/docker-manager.md)
- [Minecraft Vanilla Guide](docs/servers/minecraft-vanilla.md)
- [Team Fortress 2 Guide](docs/servers/team-fortress-2.md)
- [CS:GO Guide](docs/servers/counter-strike-global-offensive.md)

The GitHub wiki can also be updated automatically from these files when changes are pushed to `master`.

## If You Are A Developer

Use:

- [DEVELOPERS.md](DEVELOPERS.md)
- [technical_introduction.txt](technical_introduction.txt)

## Community

- Discord: https://discord.gg/8audc8Ukaq
- Twitter: https://twitter.com/sectoralpha
- Steam: http://steamcommunity.com/groups/sector-alpha

## Project

- GitHub: https://github.com/SectorAlpha/AlphaGSM
- License: GPL v3.0, see [LICENSE](LICENSE)
- Credits: see [CREDITS](CREDITS)
- Changelog: [changelog.txt](changelog.txt)
