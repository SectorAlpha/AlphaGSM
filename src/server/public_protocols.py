"""Anonymous status protocols read from game-module source. No Server import."""

from pathlib import Path
import ast

# These return a public name plus player counts. TCP, UDP, RCON, and raw
# handshakes are reachability checks, not status queries.
STRUCTURED = frozenset({"a2s", "slp", "quake", "quake2", "quakeworld", "bedrock", "ts3"})
IPV4_ONLY = frozenset({"a2s", "quake", "quake2", "quakeworld", "bedrock"})
_HOOKS = ("get_info_address", "get_query_address")
_CACHE = None


def protocol_for(game_id):
    """Return the anonymous status protocol for one canonical game id, or None."""
    if not isinstance(game_id, str):
        return None
    return _catalogue()["protocols"].get(game_id)


def queryable_games():
    """Return ``(game_id, protocol, name)`` rows for games Sector Alpha can query."""
    items = _catalogue()["games"]
    return tuple(items)


def query_port_for(game_id):
    """Return the module's usual query port, or None when the source has no single literal."""
    if not isinstance(game_id, str):
        return None
    return _catalogue()["ports"].get(game_id)


def supported_games():
    """Return ``(game_id, protocol or None, name, port or None)`` for every AlphaGSM game."""
    return tuple(_catalogue()["supported"])


def game_supported(game_id):
    """Return whether this canonical id is an AlphaGSM game module."""
    if not isinstance(game_id, str):
        return False
    return game_id in _catalogue()["known"]


def _catalogue():
    global _CACHE
    if _CACHE is None:
        _CACHE = _build()
    return _CACHE


def _build():
    root = Path(__file__).resolve().parents[1]
    modules = root / "gamemodules"
    helpers = _helper_protocols(root / "utils" / "valve_server.py")
    from server.module_catalog import load_default_module_catalog

    protocols = {}
    ports = {}
    games = []
    supported = []
    known = set()
    for game_id in load_default_module_catalog().canonical_modules:
        path = _module_file(modules, game_id)
        if path is None:
            continue
        classified = _classify(path, helpers, frozenset())
        protocol = _select(classified)
        label = classified["label"] or _fallback_name(game_id)
        port = _default_query_port(path, classified["files"])
        known.add(game_id)
        supported.append((game_id, protocol, label, port))
        if protocol is None:
            continue
        protocols[game_id] = protocol
        ports[game_id] = port
        games.append((game_id, protocol, label))
    games.sort(key=lambda item: (item[2].casefold(), item[0]))
    supported.sort(key=lambda item: (item[2].casefold(), item[0]))
    return {
        "protocols": protocols,
        "ports": ports,
        "games": tuple(games),
        "supported": tuple(supported),
        "known": frozenset(known),
    }


def _select(classified):
    info, query, valve = classified["get_info_address"], classified["get_query_address"], classified["valve"]
    if info in STRUCTURED:
        return info
    if info == "none":
        return query if query in STRUCTURED else None
    if query in STRUCTURED:
        return query
    if info == "missing" and query == "missing" and valve:
        return "a2s"
    return None


def _literal_port(node):
    if isinstance(node, ast.Constant) and type(node.value) is int and 1 <= node.value <= 65535:
        return node.value
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.isdigit():
        value = int(node.value)
        if 1 <= value <= 65535:
            return value
    return None


def _one(values):
    return next(iter(values)) if len(values) == 1 else None


def _call_name(node):
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _constants(tree):
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = _literal_port(node.value)
            if value is not None:
                found[node.targets[0].id] = value
    return found


def _port_value(node, constants):
    direct = _literal_port(node)
    if direct is not None:
        return direct
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _ports_in_tree(tree):
    """One file's query port. The module's own file wins over a file it imports."""
    constants = _constants(tree)
    queryports, valves, defaults, gameports, examples = set(), set(), set(), set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) == "define_valve_server_module":
            chosen = None
            for keyword in node.keywords:
                if keyword.arg == "port":
                    chosen = _port_value(keyword.value, constants)
            valves.add(27015 if chosen is None else chosen)
        for keyword in node.keywords:
            if keyword.arg == "default_port":
                value = _port_value(keyword.value, constants)
                if value is not None:
                    defaults.add(value)
            elif keyword.arg == "port_example":
                value = _port_value(keyword.value, constants)
                if value is not None:
                    examples.add(value)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
        ):
            value = _port_value(node.args[1], constants)
            if value is None:
                continue
            if node.args[0].value == "queryport":
                queryports.add(value)
            elif node.args[0].value == "port":
                gameports.add(value)
    return _one(queryports) or _one(valves) or _one(defaults) or _one(gameports) or _one(examples)


def _default_query_port(primary, files):
    """Read the usual query port from the game module, then from the hook it imports."""
    own = _ports_in_tree(ast.parse(primary.read_text(encoding="utf-8")))
    if own is not None:
        return own
    inherited = set()
    for path in files:
        if path == primary:
            continue
        value = _ports_in_tree(ast.parse(path.read_text(encoding="utf-8")))
        if value is not None:
            inherited.add(value)
    return _one(inherited)


def _module_file(modules, game_id):
    base = modules.joinpath(*game_id.split("."))
    for candidate in (base.with_suffix(".py"), base / "main.py", base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _helper_protocols(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            literals, aliases = _returns(node)
            if literals and not aliases:
                found[node.name] = set(literals)
    return found


def _classify(path, helpers, stack):
    if path in stack:
        return {hook: "missing" for hook in _HOOKS} | {"valve": False, "label": "", "files": frozenset()}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    local = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in _HOOKS:
            local[node.name] = _returns(node)
    imported = {}
    files = {path}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        names = {alias.name for alias in node.names}
        if "*" not in names and not names.intersection(_HOOKS):
            continue
        target = _relative_module(path, node.module, node.level)
        if target is None:
            continue
        parent = _classify(target, helpers, stack | {path})
        files.update(parent["files"])
        for hook in _HOOKS:
            if hook not in local and (hook in names or "*" in names):
                imported.setdefault(hook, parent[hook])
    classified = {
        "valve": _calls(tree, "define_valve_server_module"),
        "label": _label(tree),
        "files": frozenset(files),
    }
    for hook in _HOOKS:
        if hook in local:
            protocols = _resolve(hook, local, helpers, frozenset())
            classified[hook] = _pick(protocols)
        else:
            classified[hook] = imported.get(hook, "missing")
    return classified


def _returns(function):
    literals, aliases = set(), set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value
        if isinstance(value, ast.Tuple) and len(value.elts) >= 3 and isinstance(value.elts[2], ast.Constant):
            if isinstance(value.elts[2].value, str):
                literals.add(value.elts[2].value)
                continue
        name = _called_name(value)
        if name:
            aliases.add(name)
    return literals, aliases


def _called_name(value):
    if not isinstance(value, ast.Call):
        return None
    func = value.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    if (
        isinstance(func, ast.Call)
        and isinstance(func.func, ast.Name)
        and func.func.id == "_package_override"
        and len(func.args) >= 2
        and isinstance(func.args[1], ast.Name)
    ):
        return func.args[1].id
    return None


def _resolve(name, local, helpers, seen):
    if name in seen:
        return {"?"}
    if name not in local:
        return set(helpers[name]) if name in helpers else {"?"}
    literals, aliases = local[name]
    protocols = set(literals)
    for alias in aliases:
        if alias in local:
            protocols |= _resolve(alias, local, helpers, seen | {name})
        elif alias in helpers:
            protocols |= helpers[alias]
        else:
            protocols.add("?")
    return protocols


def _pick(protocols):
    if not protocols or "?" in protocols or not protocols <= STRUCTURED or len(protocols) != 1:
        return "none"
    return next(iter(protocols))


def _calls(tree, name):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id == name) or (isinstance(func, ast.Attribute) and func.attr == name):
            return True
    return False


def _fallback_name(game_id):
    if game_id.startswith("minecraft."):
        return "Minecraft " + game_id.split(".", 1)[1].replace("_", " ").title()
    return game_id


def _label(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = (isinstance(func, ast.Name) and func.id == "define_valve_server_module") or (
            isinstance(func, ast.Attribute) and func.attr == "define_valve_server_module"
        )
        if not called:
            continue
        for keyword in node.keywords:
            if keyword.arg == "game_name" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str) and keyword.value.value.strip():
                    return keyword.value.value.strip()
    text = ast.get_docstring(tree) or ""
    first = text.split(".", 1)[0].strip()
    marker = "-specific"
    if marker in first:
        return first.split(marker, 1)[0].strip() or ""
    for suffix in (
        " dedicated server lifecycle helpers",
        " dedicated server helpers",
        " server lifecycle helpers",
        " lifecycle helpers",
    ):
        if first.endswith(suffix):
            return first[: -len(suffix)].strip()
    return ""


def _relative_module(path, module, level):
    if level < 1:
        return None
    base = path.parent
    for _ in range(level - 1):
        base = base.parent
    parts = module.split(".") if module else []
    candidate = base.joinpath(*parts)
    for item in (candidate.with_suffix(".py"), candidate / "__init__.py", candidate / "main.py"):
        if item.is_file():
            return item
    return None
