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

## What You Need

You need:

- Python 3
- `screen`
- the Python packages in `requirements.txt`

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

CS:GO:

```bash
./alphagsm mycsgo create csgo
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
bash ./smoke_tests/run_minecraft_vanilla.sh
bash ./smoke_tests/run_tf2.sh
```

These scripts are useful because they show a full real flow:

1. create the server
2. run setup
3. start it
4. check it
5. stop it cleanly

## Step-By-Step Server Guides

- [Documentation Index](docs/README.md)
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
