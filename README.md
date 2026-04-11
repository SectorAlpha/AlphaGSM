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

If you want the Docker-manager route, there is also a root wrapper script:

For many first-time setups, this is the quickest way to get started because it
avoids most of the host-side Python, Java, and system-package setup.

```bash
./alphagsm-docker start
./alphagsm-docker mymc create minecraft.vanilla
```

The wrapper keeps runtime-image pre-pull off by default so it works without
GHCR login for a first run. By default it tries to pull the latest manager
image from GHCR and falls back to a local build if that pull fails. If you are
working on AlphaGSM itself, `./alphagsm-docker start --develop` switches the
wrapper into a local-build developer mode.

See [Run AlphaGSM In Docker](docs/docker-manager.md).

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

## Fast Start

If you want the quickest first run, start with the Docker-manager path above.
The host install below is still the right option when you want AlphaGSM running
directly on the machine instead of through Docker.

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

Show help:

```bash
./alphagsm --help
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
