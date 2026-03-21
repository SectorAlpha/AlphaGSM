# AlphaGSM

AlphaGSM is a command-line tool that helps you download, set up, start, stop, update, and back up game servers.

If you are not very technical, the short version is:

1. Install the few things AlphaGSM needs.
2. Run one command to create a server.
3. Run one command to set it up.
4. Start it.

AlphaGSM keeps the server running inside `screen`, so you do not need to keep one terminal window open for the server process yourself.

## What Can It Manage?

AlphaGSM currently includes built-in support for:

- Minecraft Vanilla
- Minecraft Bungeecord
- Custom Minecraft server jars
- Team Fortress 2
- Counter-Strike: Global Offensive

There are also alias names such as `minecraft`, `tf2`, and `csgo`.

## What You Need

Most people only need:

- Python 3
- `screen`
- the Python packages in `requirements.txt`

Some servers need extra software:

- Minecraft needs Java
- Steam-based servers such as TF2 and CS:GO need SteamCMD runtime libraries

## Quick Start

### 1. Download AlphaGSM

Clone the repository or download it, then move into the project directory.

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a config file

```bash
cp alphagsm.conf-template alphagsm.conf
```

For many single-user setups, the default config is enough to get started.

### 4. Create a server

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

### 5. Set the server up

```bash
./alphagsm mymc setup
```

The setup command may ask questions such as:

- which port to use
- where to install the server
- which version to download
- where Java lives for Minecraft

### 6. Start the server

```bash
./alphagsm mymc start
```

### 7. Check if it is running

```bash
./alphagsm mymc status
```

### 8. Stop the server later

```bash
./alphagsm mymc stop
```

## Useful Everyday Commands

Send a message to players:

```bash
./alphagsm mymc message "Server restarting soon"
```

Back a server up:

```bash
./alphagsm mymc backup
```

Update a Steam game server:

```bash
./alphagsm mytf2 update
./alphagsm mytf2 update -r
```

Show full help:

```bash
./alphagsm --help
```

## Where To Find Help

If you want step-by-step guides for specific servers, start here:

- [Documentation Index](docs/README.md)
- [Minecraft Vanilla Guide](docs/servers/minecraft-vanilla.md)
- [Team Fortress 2 Guide](docs/servers/team-fortress-2.md)
- [CS:GO Guide](docs/servers/counter-strike-global-offensive.md)

If you are developing or changing AlphaGSM itself, read:

- [DEVELOPERS.md](DEVELOPERS.md)
- [technical_introduction.txt](technical_introduction.txt)

## Testing and Quality Checks

AlphaGSM now includes:

- unit tests
- integration tests
- smoke tests
- pylint linting
- unit test coverage reporting

Run the unit tests:

```bash
pytest tests
```

Run the lint checks:

```bash
bash ./lint.sh
```

Run the integration test suite when you explicitly want it:

```bash
ALPHAGSM_RUN_INTEGRATION=1 pytest integration_tests
```

Run the streamed smoke-test examples:

```bash
bash ./smoke_tests/run_minecraft_vanilla.sh
bash ./smoke_tests/run_tf2.sh
```

These smoke runners are also useful as real working examples of how AlphaGSM creates a temporary config, installs a server, starts it, checks it, and shuts it down again.

## Community

- Discord: https://discord.gg/8audc8Ukaq
- Twitter: https://twitter.com/sectoralpha
- Steam: http://steamcommunity.com/groups/sector-alpha

## Project

- GitHub: https://github.com/SectorAlpha/AlphaGSM
- License: GPL v3.0, see [LICENSE](LICENSE)
- Credits: see [CREDITS](CREDITS)
