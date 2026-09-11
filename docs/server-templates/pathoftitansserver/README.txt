This directory includes the upstream-documented Path of Titans runtime config example.

Use `PathOfTitans/Saved/Config/WindowsServer/Game.ini` as the official documented Windows example path for native server settings.
On non-Windows servers, the platform folder under `PathOfTitans/Saved/Config/` differs, but `Game.ini` remains the native config file.
AlphaGSM still manages `ServerGUID`, `BranchKey`, `Database`, and the main port through launch arguments rather than `Game.ini`.
