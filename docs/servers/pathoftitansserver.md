# Path of Titans

This guide covers the `pathoftitansserver` module in AlphaGSM.

## Requirements

- `screen`
- an Alderon auth token for the hosting account, or a staged server archive override/tree
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypathofti create pathoftitansserver
```

Run setup:

```bash
alphagsm mypathofti setup
```

`pathoftitansserver` is supported in `ENABLED (BYO)` mode. Before `setup` or
`start`, either:

- set `auth_token` to an Alderon host account token so AlphaGSM can install via
  `AlderonGamesCmd`, or
- stage a direct archive override/server tree and point `url` at that archive if
  you are using a prepackaged payload

Start it:

```bash
alphagsm mypathofti start
```

Check it:

```bash
alphagsm mypathofti status
```

Stop it:

```bash
alphagsm mypathofti stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- installs via `AlderonGamesCmd` when `auth_token` is present, or uses a direct
  archive override when `url` is set

Suggested flow:

```bash
alphagsm mypathofti create pathoftitansserver
alphagsm mypathofti set auth_token your-alderon-token
alphagsm mypathofti setup -n 7777 /path/to/pathoftitansserver
alphagsm mypathofti start
```

Or with a staged archive override:

```bash
alphagsm mypathofti create pathoftitansserver
alphagsm mypathofti set url https://example.invalid/pathoftitans-server.zip
alphagsm mypathofti setup -n 7777 /path/to/pathoftitansserver
alphagsm mypathofti start
```

## Useful Commands

```bash
alphagsm mypathofti update
alphagsm mypathofti backup
alphagsm mypathofti set auth_token your-alderon-token
alphagsm mypathofti set url https://example.invalid/pathoftitans-server.zip
```

## Notes

- Module name: `pathoftitansserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `PathOfTitansServer.sh`
- **Location**: `<install_dir>/PathOfTitansServer.sh`
- **Engine**: Custom

### Server Configuration

- **Config file**: `PathOfTitans/Saved/Config/WindowsServer/Game.ini`
- **Notes**: upstream docs use `WindowsServer` for the Windows example path; the platform folder differs on non-Windows servers. AlphaGSM still manages `ServerGUID`, `BranchKey`, `Database`, and `-port` through launch arguments.
- **Max players**: `100`
- **Template**: See [server-templates/pathoftitansserver/](../server-templates/pathoftitansserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
