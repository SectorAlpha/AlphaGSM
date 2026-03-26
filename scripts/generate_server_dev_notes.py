#!/usr/bin/env python3
"""Extract server info from game modules and generate developer notes.

Reads every game module under src/gamemodules/ and produces:
  1. Developer Notes sections appended to docs/servers/<module>.md
  2. Config templates in docs/server-templates/<module>/

Usage:
    PYTHONPATH=.:src python3 scripts/generate_server_dev_notes.py
"""

import ast
import os
import re
import sys
import textwrap

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(REPO, "src", "gamemodules")
DOCS_DIR = os.path.join(REPO, "docs", "servers")
TEMPLATES_DIR = os.path.join(REPO, "docs", "server-templates")

# ---------------------------------------------------------------------------
# AST-based extraction (no imports needed, safe for broken modules)
# ---------------------------------------------------------------------------

def extract_valve_params(source):
    """Extract define_valve_server_module() keyword arguments from source."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "define_valve_server_module":
                params = {}
                for kw in node.keywords:
                    if isinstance(kw.value, ast.Constant):
                        params[kw.arg] = kw.value.value
                    elif isinstance(kw.value, ast.Name) and kw.value.id == "None":
                        params[kw.arg] = None
                return params
    return None


def extract_non_valve_info(source):
    """Extract key info from non-Valve game modules via AST."""
    info = {}
    tree = ast.parse(source)

    for node in ast.walk(tree):
        # Top-level assignments: steam_app_id, etc.
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    name = target.id
                    if name in ("steam_app_id", "steam_anonymous_login_possible"):
                        info[name] = node.value.value

    # Look for configure() defaults and get_start_command() patterns
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # server.data.setdefault("configfile", ...)
            if (isinstance(func, ast.Attribute) and func.attr == "setdefault"
                    and len(node.args) >= 2):
                key_node, val_node = node.args[0], node.args[1]
                if isinstance(key_node, ast.Constant) and isinstance(val_node, ast.Constant):
                    key = key_node.value
                    if key in ("configfile", "port", "exe_name", "udpport",
                               "httpport", "maxplayers", "defaultmap",
                               "backupfiles", "rconport"):
                        info[key] = val_node.value

    # Look for exe_name in configure() defaults
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "configure":
            for default in node.args.defaults + node.args.kw_defaults:
                pass  # complex to match, skip
            # Check for exe_name keyword default
            for kwarg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                if kwarg.arg == "exe_name" and isinstance(default, ast.Constant):
                    info.setdefault("exe_name", default.value)

    return info


def find_config_refs(source):
    """Find config file references in source code."""
    patterns = [
        r'"([^"]*\.cfg)"',
        r'"([^"]*\.ini)"',
        r'"([^"]*\.yaml)"',
        r'"([^"]*\.json)"',
        r'"([^"]*\.toml)"',
        r'"([^"]*\.xml)"',
        r'"([^"]*\.properties)"',
        r'"([^"]*server\.config)"',
    ]
    refs = set()
    for pat in patterns:
        for m in re.finditer(pat, source):
            val = m.group(1)
            # Filter out obvious non-config patterns
            if val and not val.startswith("http") and len(val) < 80:
                refs.add(val)
    return sorted(refs)


def find_map_mod_dirs(source, game_dir=None):
    """Infer map and mod directory paths from source."""
    maps_dir = None
    mods_dir = None
    workshop = "No"

    if game_dir:
        maps_dir = f"{game_dir}/maps/"
        # Source engine standard
        if "addons" in source.lower():
            mods_dir = f"{game_dir}/addons/"
        # GoldSrc
        if "dlls" in source.lower():
            mods_dir = f"{game_dir}/dlls/ (Metamod)"

    # Minecraft
    if "server.properties" in source:
        maps_dir = "world/"
        if "plugins" in source.lower():
            mods_dir = "plugins/"
        elif "mods" in source.lower():
            mods_dir = "mods/"

    # Workshop
    if "workshop" in source.lower():
        workshop = "Yes"

    return maps_dir, mods_dir, workshop


# ---------------------------------------------------------------------------
# Generate developer notes markdown
# ---------------------------------------------------------------------------

def generate_valve_notes(module_name, params, source):
    """Generate Developer Notes for a Valve server module."""
    engine = params.get("engine", "source")
    exe = params.get("executable", "srcds_run")
    game_dir = params.get("game_dir", "")
    config_sub = params.get("config_subdir", "cfg")
    config_file = params.get("config_default", "server.cfg")
    default_map = params.get("default_map", "")
    max_players = params.get("max_players", "")
    port = params.get("port", 27015)
    client_port = params.get("client_port")
    sourcetv_port = params.get("sourcetv_port")
    steam_port = params.get("steam_port")
    app_id = params.get("steam_app_id", "")
    app_id_mod = params.get("app_id_mod")
    game_name = params.get("game_name", module_name)

    engine_label = "Source" if engine == "source" else "GoldSrc (HLDS)"
    config_path = os.path.join(game_dir, config_sub, config_file).replace('//', '/')
    maps_dir = f"{game_dir}/maps/"
    if engine == "source":
        mods_dir = f"{game_dir}/addons/"
        mods_note = f"Copy addon folders into `{mods_dir}`."
    else:
        mods_dir = f"{game_dir}/dlls/"
        mods_note = f"Use Metamod in `{mods_dir}` or AMX Mod X in `{game_dir}/addons/amxmodx/`."

    workshop = "Yes" if "workshop" in source.lower() else "No"
    mapcycle_path = os.path.join(game_dir, config_sub, 'mapcycle.txt').replace('//', '/')
    map_install = f"Copy `.bsp` files into `{maps_dir}` and add to `{mapcycle_path}`."

    ports_lines = [f"  - Game port: `{port}` (UDP)"]
    if client_port:
        ports_lines.append(f"  - Client port: `{client_port}` (UDP)")
    if sourcetv_port:
        ports_lines.append(f"  - SourceTV port: `{sourcetv_port}` (UDP)")
    if steam_port:
        ports_lines.append(f"  - Steam port: `{steam_port}` (UDP)")
    ports_block = "\n".join(ports_lines)

    mod_line = ""
    if app_id_mod:
        mod_line = f"\n- **Mod App ID**: `{app_id_mod}`"

    notes = f"""## Developer Notes

### Run File

- **Executable**: `{exe}`
- **Location**: `<install_dir>/{exe}`
- **Engine**: {engine_label}
- **SteamCMD App ID**: `{app_id}`{mod_line}

### Server Configuration

- **Config file**: `{config_path}`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `{port}`
- **Default map**: `{default_map}`
- **Max players**: `{max_players}`
- **Ports**:
{ports_block}
- **Template**: See [server-templates/{module_name}/]({{}})

### Maps and Mods

- **Map directory**: `{maps_dir}`
- **Mod directory**: `{mods_dir}`
- **Workshop support**: {workshop}
- **Map install**: {map_install}
- **Mod install**: {mods_note}
"""
    return notes.strip()


def generate_non_valve_notes(module_name, info, source):
    """Generate Developer Notes for a non-Valve server module."""
    app_id = info.get("steam_app_id", "")
    exe_name = info.get("exe_name", "")
    config_file = info.get("configfile", "")
    port = info.get("port", info.get("udpport", info.get("httpport", "")))
    max_players = info.get("maxplayers", "")

    is_steamcmd = bool(app_id) or "steamcmd" in source.lower()
    config_refs = find_config_refs(source)
    maps_dir, mods_dir, workshop = find_map_mod_dirs(source)

    # Determine engine/type
    if "minecraft" in module_name.lower() or "server.properties" in source:
        engine_label = "Java / Custom"
    elif is_steamcmd:
        engine_label = "Custom (SteamCMD)"
    else:
        engine_label = "Custom"

    lines = ["## Developer Notes", "", "### Run File", ""]
    if exe_name:
        lines.append(f"- **Executable**: `{exe_name}`")
        lines.append(f"- **Location**: `<install_dir>/{exe_name}`")
    else:
        lines.append("- **Executable**: See game module source")
    lines.append(f"- **Engine**: {engine_label}")
    if app_id:
        lines.append(f"- **SteamCMD App ID**: `{app_id}`")

    lines.extend(["", "### Server Configuration", ""])
    if config_file:
        lines.append(f"- **Config file**: `{config_file}`")
    elif config_refs:
        lines.append(f"- **Config files**: {', '.join(f'`{r}`' for r in config_refs[:5])}")
    else:
        lines.append("- **Config file**: See game module source")
    if port:
        lines.append(f"- **Default port**: `{port}`")
    if max_players:
        lines.append(f"- **Max players**: `{max_players}`")
    lines.append(f"- **Template**: See [server-templates/{module_name}/]({{}}) if available")

    lines.extend(["", "### Maps and Mods", ""])
    if maps_dir:
        lines.append(f"- **Map directory**: `{maps_dir}`")
    else:
        lines.append("- **Map directory**: Check game documentation")
    if mods_dir:
        lines.append(f"- **Mod directory**: `{mods_dir}`")
    else:
        lines.append("- **Mod directory**: Check game documentation")
    lines.append(f"- **Workshop support**: {workshop}")

    return "\n".join(lines)


def generate_valve_template(module_name, params):
    """Generate a server.cfg template for a Valve server."""
    game_name = params.get("game_name", module_name)
    default_map = params.get("default_map", "")
    max_players = params.get("max_players", 16)
    port = params.get("port", 27015)

    return f"""// {game_name} Dedicated Server Configuration
// Place this file at: <game_dir>/<config_subdir>/server.cfg

// Server identity
hostname "My {game_name} Server"
sv_password ""
rcon_password "changeme"

// Network
sv_maxrate 0
sv_minrate 0
sv_maxupdaterate 66
sv_minupdaterate 10

// Game settings
mp_timelimit 30
mp_maxrounds 0

// Logging
log on
sv_logbans 1
sv_logecho 1
sv_logfile 1

// Default map: {default_map}
// Default max players: {max_players}
// Default port: {port}
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_all_modules():
    """Find all game module .py files."""
    modules = {}
    for root, dirs, files in os.walk(MODULES_DIR):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                path = os.path.join(root, f)
                name = f[:-3]
                # For subpackage modules like minecraft/vanilla.py
                rel = os.path.relpath(root, MODULES_DIR)
                if rel != ".":
                    # Skip DEFAULT.py aliases
                    if name == "DEFAULT":
                        continue
                    name = rel.replace(os.sep, "-") + "-" + name
                modules[name] = path
    return modules


def process_module(name, path):
    """Process a single game module and return (notes, template_content)."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    # Check for ALIAS_TARGET — skip aliases
    if "ALIAS_TARGET" in source:
        return None, None

    # Try Valve extraction first
    valve_params = extract_valve_params(source)
    if valve_params:
        notes = generate_valve_notes(name, valve_params, source)
        template = generate_valve_template(name, valve_params)
        return notes, template

    # Non-Valve
    info = extract_non_valve_info(source)
    notes = generate_non_valve_notes(name, info, source)
    return notes, None


def update_doc(name, notes):
    """Append Developer Notes to a server doc if not already present."""
    # Map module name to doc file
    doc_path = os.path.join(DOCS_DIR, name + ".md")
    if not os.path.isfile(doc_path):
        return False

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Don't duplicate
    if "## Developer Notes" in content:
        return False

    # Fix template links
    notes = notes.replace("({})", f"(../server-templates/{name}/)")
    notes = notes.replace('//', '/')  # clean up double slashes except in URLs
    # Restore any broken protocol slashes
    notes = notes.replace('http:/', 'http://').replace('https:/', 'https://')

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n\n" + notes + "\n")
    return True


def write_template(name, template):
    """Write a config template file."""
    tpl_dir = os.path.join(TEMPLATES_DIR, name)
    os.makedirs(tpl_dir, exist_ok=True)
    tpl_path = os.path.join(tpl_dir, "server.cfg")
    if os.path.isfile(tpl_path):
        return False
    with open(tpl_path, "w", encoding="utf-8") as f:
        f.write(template)
    return True


def main():
    modules = find_all_modules()
    print(f"Found {len(modules)} game modules")

    docs_updated = 0
    templates_created = 0
    skipped = 0

    for name, path in sorted(modules.items()):
        notes, template = process_module(name, path)
        if notes is None:
            skipped += 1
            continue

        if update_doc(name, notes):
            docs_updated += 1
            print(f"  Updated doc: {name}")

        if template and write_template(name, template):
            templates_created += 1
            print(f"  Created template: {name}")

    print(f"\nDone: {docs_updated} docs updated, {templates_created} templates created, {skipped} aliases skipped")


if __name__ == "__main__":
    main()
