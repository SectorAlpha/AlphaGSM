# Standalone AlphaGSM

The release executable contains AlphaGSM and its Python runtime. You do not need
a Python installation or a source checkout. Game servers still need their own
runtime, such as Java, SteamCMD, or Docker, and some require accounts or owned
files. Use the matching game guide for those prerequisites.

Download the executable for your operating system and processor from
[GitHub Releases](https://github.com/SectorAlpha/AlphaGSM/releases). Keep its
`.sha256` file if you want to verify the download. On Linux/macOS, rename the
executable to `alphagsm` and make it executable:

```bash
chmod +x alphagsm
./alphagsm --version
./alphagsm --help
```

On Windows, rename it to `alphagsm.exe` and run it from PowerShell:

```powershell
.\alphagsm.exe --version
.\alphagsm.exe --help
```

Choose a directory you can write to for your server files. AlphaGSM keeps user
settings under `~/.alphagsm` on Linux/macOS or `%LOCALAPPDATA%\alphagsm` on
Windows. The executable directory can be read-only. An optional `alphagsm.conf`
beside the executable supplies system defaults; it is not required for first
run. If you explicitly set `ALPHAGSM_CONFIG_LOCATION`, that file must exist.

For example, after installing the Java version required by Minecraft:

```bash
./alphagsm mymc create minecraft.vanilla
./alphagsm mymc setup -n -l 25565 "$HOME/minecraft-server"
./alphagsm mymc start
./alphagsm mymc query
./alphagsm mymc info --json
./alphagsm mymc stop
```

On Windows, use `.\alphagsm.exe` and a Windows server directory instead. Read
Minecraft's license before using `-n` to accept it. The subprocess backend
supports console commands and graceful shutdown across separate terminal
invocations without installing screen or tmux. Its `connect` command displays
logs; use `send` for console input. Unix cron activation requires cron; Windows
startup scheduling is not supplied by these binaries.

## Platform coverage

The binary workflow builds and tests these explicit targets using
[GitHub-hosted runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners):

| Artifact | Build/test baseline |
| --- | --- |
| linux-X64 | Ubuntu 22.04, x86-64 |
| linux-ARM64 | Ubuntu 24.04, ARM64 |
| windows-X64 | Windows Server 2022, x86-64 |
| macos-ARM64 | macOS 15, Apple Silicon |
| macos-X64 | macOS 15, Intel |

These are validation targets, not a claim that all games work on every target.
Only successful CI for the release commit establishes that release's binary
coverage. The full game-server matrix retains Ubuntu 24.04 as its baseline.
Linux artifacts require compatible glibc; Alpine/musl and older baselines are
not covered. Windows ARM64 is not currently a build target.

Docker-capable modules can use the Docker runtime when the host has a working
Docker daemon and compatible container architecture. The executable includes
the repository's runtime image build files so the default image fallback does
not require a checkout. Initial image builds require network access and space.

## Updates and diagnostics

```bash
./alphagsm self-update --check
./alphagsm self-update
./alphagsm mymc doctor --json
```

Self-update verifies the download checksum and stages replacement beside the
installed executable. The directory must be writable. On Windows, replacement
is scheduled for after the CLI exits; inspect the printed result-file path to
confirm completion. An update failure preserves or restores the previous
executable. Temporary Windows helper files can be removed after completion.

`doctor --json` emits structured, redacted diagnostics and returns a failing
exit code when a check fails. A stopped server alone is not an error. Each
successful setup/update also records installation evidence under its datastore
directory in `.provenance/<server>.installation.json`. Unknown versions and checksums remain
unknown; the record does not imply a full lifecycle test passed.

If a command reports that server state is busy, another command holds its lock.
Wait for it to finish. Do not delete lock files while AlphaGSM is running. The
operating system releases locks when their owning process exits.

See [the developer release contract](../DEVELOPERS.md#standalone-release-contract)
for maintainer signing setup and CI requirements.
