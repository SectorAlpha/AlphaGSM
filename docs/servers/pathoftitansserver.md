# Path of Titans

This guide covers the `pathoftitansserver` module in AlphaGSM.

## Requirements

- `screen`
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
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mypathofti update
alphagsm mypathofti backup
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
