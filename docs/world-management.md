# Creating and resetting worlds

## Create a first world without answering console prompts

Terraria, TShock and Necesse support:

```bash
alphagsm myserver start --autocreate
```

This uses the configured `world` setting. Terraria and TShock also use
`worldname` and `worldsize` (`1` small, `2` medium, `3` large).

**If the configured world already exists, `--autocreate` does nothing:** the
launch is identical to plain `start`. It does not replace, repair, or delete
an existing file. Without creation, use the native world-selection prompt:

```bash
alphagsm myserver start
alphagsm myserver connect
```

Interactive selection needs a console backend that accepts keyboard input,
such as screen, tmux, or Docker attach. The subprocess backend's `connect`
only follows logs. Unattended smoke and integration tests request
`--autocreate` explicitly for their fresh installations.

Minecraft and Rust already create missing worlds as part of normal startup;
they do not need this option. Rust keeps using its configured seed and size.

New Necesse installations store data in the install directory and mount that
same directory into Docker. For an older installation, set `datadir` to its
**existing** Necesse data directory before using creation or reset commands.
On Linux the native default is usually `~/.config/Necesse`; check where your
save is located first. This setting does not move existing saves.

```bash
alphagsm mynecserve set datadir /path/to/existing/Necesse
```

## Start over

Stop the server, then reset its configured world:

```bash
alphagsm myserver stop
alphagsm myserver reset-world
```

`reset-world` is an alias for `wipe`. Both list the exact existing target
paths before asking `Permanently delete this world data? [y/N]`. Listed
directories include all their contents. Enter `y` or `yes` to delete them;
Enter, other answers, and end of input cancel. Deletion is permanent.

For automation, `-Y` skips confirmation while still printing the targets:

```bash
alphagsm myserver reset-world -Y
```

The command refuses to run while the server is running. It preserves server
configuration, plugins, and worlds outside the listed targets. Missing world
files are a no-op. Make a backup first if you want to keep the old world.

| Module | World data removed |
| --- | --- |
| Minecraft Java (`minecraft`, `minecraft.vanilla`, `minecraft.custom`, `minecraft.tekkit`) | The configured world directory, including its dimensions and player data |
| `minecraft.paper` | The configured world, plus its `_nether` and `_the_end` directories |
| `minecraft.bedrock` | The configured directory under `worlds/` |
| Terraria and TShock | The configured `.wld` file and its `.bak`/`.bak2` backups under `Worlds/` |
| `necserver` | The configured compressed or uncompressed save under its explicit `datadir` |
| `rust` | Procedural `.map`, `.sav`, and numbered save backups matching the configured seed/size in `server/my_server_identity/`; blueprints and other player databases remain |

Minecraft reads `level-name` from `server.properties` when present and checks
that existing targets contain world metadata. Directories without recognizable
world metadata, and unusual escaped or continued properties, require a manual
reset rather than guessing which directory to delete. Rust custom maps and custom identities are outside
the reset command's current scope. Other modules report when reset is unsupported.

After resetting Terraria, TShock, or Necesse, create the next world with:

```bash
alphagsm myserver start --autocreate
```

For Minecraft and Rust, run ordinary `start` again. Reusing the same seed and
world-generation settings may reproduce the same terrain with fresh progress.
