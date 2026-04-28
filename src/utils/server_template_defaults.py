"""Helpers for AlphaGSM-oriented template defaults."""

from __future__ import annotations

import ast
import re
from collections import OrderedDict
from pathlib import Path

from server.module_catalog import load_default_module_catalog


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = REPO_ROOT / "docs" / "server-templates"
MODULE_ROOT = REPO_ROOT / "src" / "gamemodules"
DOCS_ROOT = REPO_ROOT / "docs" / "servers"
MODULE_CATALOG = load_default_module_catalog()
TEMPLATE_MODULE_ALIASES = {
    "arma3-headless": "arma3headlessserver",
}
DOCUMENTED_RUNTIME_TEMPLATE_PATHS = {
    "enshrouded": Path("enshrouded_server.json"),
    "interstellarriftserver": Path("server.json"),
    "nightingale": Path("NWX/Config/ServerSettings.ini"),
    "pathoftitansserver": Path("PathOfTitans/Saved/Config/WindowsServer/Game.ini"),
    "starbound": Path("storage/starbound_server.config"),
}
IGNORED_TEMPLATE_DIRS = {"_template"}
MODULE_PATH_KEYS = (
    "configfile",
    "settingsfile",
    "eventfile",
    "eventrulesfile",
    "connectionfile",
    "servercfg",
)
IGNORED_DEFAULT_KEYS = {
    "Steam_AppID",
    "Steam_anonymous_login_possible",
    "backup",
    "backupfiles",
    "container_name",
    "current_url",
    "dir",
    "download_name",
    "env",
    "exe_name",
    "image",
    "mounts",
    "network_mode",
    "runtime",
    "runtime_family",
    "stop_mode",
    "url",
    "version",
}
SIMPLE_STRING_RE = re.compile(r"^[A-Za-z0-9_./:-]+$")
ASSIGNMENT_RE = re.compile(r"^([A-Za-z0-9_]+)=(.*)$")
CONFIG_LINE_RE = re.compile(r"\*\*Config files?\*\*:")
BACKTICK_RE = re.compile(r"`([^`]+)`")


class _ExpressionEvaluator:
    """Evaluate the small subset of module AST nodes used for defaults."""

    def __init__(self, env: dict[str, object]):
        self.env = env

    def eval(self, node: ast.AST | None) -> object:
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.env.get(node.id, f"<{node.id}>")
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "server" and node.attr == "name":
                return "<server name>"
            return None
        if isinstance(node, ast.List):
            return [self.eval(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.eval(item) for item in node.elts)
        if isinstance(node, ast.Dict):
            return {
                self.eval(key): self.eval(value)
                for key, value in zip(node.keys, node.values)
            }
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value = self.eval(node.operand)
            if isinstance(value, (int, float)):
                return -value
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            left = self.eval(node.left)
            right = self.eval(node.right)
            try:
                return left % right
            except Exception:
                return None
        if isinstance(node, ast.JoinedStr):
            rendered = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    rendered.append(str(value.value))
                elif isinstance(value, ast.FormattedValue):
                    rendered.append(str(self.eval(value.value)))
            return "".join(rendered)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"bool", "float", "int", "str"}:
                if len(node.args) != 1:
                    return None
                value = self.eval(node.args[0])
                try:
                    return {"bool": bool, "float": float, "int": int, "str": str}[node.func.id](value)
                except Exception:
                    return None
        return None


class _ConfigureDefaultCollector(ast.NodeVisitor):
    """Collect defaults exposed through ``configure(...)``."""

    def __init__(self, evaluator: _ExpressionEvaluator):
        self.evaluator = evaluator
        self.defaults: OrderedDict[str, object] = OrderedDict()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if (
                isinstance(owner, ast.Attribute)
                and owner.attr == "data"
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "server"
            ):
                if node.func.attr in {"get", "setdefault"} and len(node.args) >= 2:
                    key = self.evaluator.eval(node.args[0])
                    value = self.evaluator.eval(node.args[1])
                    if isinstance(key, str) and key not in self.defaults:
                        self.defaults[key] = value
                self.generic_visit(node)
                return

        helper_name = None
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "gamemodule_common":
                helper_name = node.func.attr

        if helper_name == "set_server_defaults" and len(node.args) >= 2:
            defaults = self.evaluator.eval(node.args[1])
            if isinstance(defaults, dict):
                for key, value in defaults.items():
                    if isinstance(key, str) and key not in self.defaults:
                        self.defaults[key] = value
        elif helper_name == "configure_port":
            for keyword in node.keywords:
                if keyword.arg != "default_port":
                    continue
                value = self.evaluator.eval(keyword.value)
                if value is not None and "port" not in self.defaults:
                    self.defaults["port"] = value
                break

        self.generic_visit(node)


class _SupportedKeyCollector(ast.NodeVisitor):
    """Collect top-level datastore keys accepted by ``checkvalue(...)``."""

    def __init__(self) -> None:
        self.keys: OrderedDict[str, None] = OrderedDict()

    def visit_If(self, node: ast.If) -> None:
        for key in self._extract_keys(node.test):
            if key != "backup" and key not in self.keys:
                self.keys[key] = None
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        helper_name = None
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "gamemodule_common":
                helper_name = node.func.attr

        if helper_name in {"handle_basic_checkvalue", "handle_setting_schema_checkvalue"}:
            for keyword in node.keywords:
                if keyword.arg in {
                    "int_keys",
                    "str_keys",
                    "bool_keys",
                    "resolved_int_keys",
                    "resolved_str_keys",
                    "raw_int_keys",
                    "raw_str_keys",
                }:
                    for key in self._extract_string_sequence(keyword.value):
                        if key != "backup" and key not in self.keys:
                            self.keys[key] = None

        self.generic_visit(node)

    def _extract_keys(self, node: ast.AST) -> list[str]:
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            return []
        left = node.left
        if not (
            isinstance(left, ast.Subscript)
            and isinstance(left.value, ast.Name)
            and left.value.id == "key"
            and isinstance(left.slice, ast.Constant)
            and left.slice.value == 0
        ):
            return []
        comparator = node.comparators[0]
        if isinstance(node.ops[0], ast.Eq):
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                return [comparator.value]
            return []
        if isinstance(node.ops[0], ast.In) and isinstance(comparator, (ast.List, ast.Tuple)):
            return [
                item.value
                for item in comparator.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
        return []

    def _extract_string_sequence(self, node: ast.AST) -> list[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return [
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
        return []


def iter_alphagsm_example_templates() -> list[Path]:
    """Return every AlphaGSM-oriented example template in source order."""

    return sorted(
        path
        for path in TEMPLATE_ROOT.rglob("alphagsm-example.cfg")
        if path.parent.name not in IGNORED_TEMPLATE_DIRS
    )


def parse_template_assignments(text: str) -> OrderedDict[str, str]:
    """Parse simple ``key=value`` lines from an example template."""

    assignments: OrderedDict[str, str] = OrderedDict()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = ASSIGNMENT_RE.match(line)
        if match:
            assignments[match.group(1)] = match.group(2)
    return assignments


def extract_template_defaults(template_dir_name: str) -> OrderedDict[str, object]:
    """Extract the AlphaGSM-exposed defaults for one template directory."""

    module_path = _resolve_module_path(template_dir_name)
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    configure_node = functions.get("configure")
    checkvalue_node = functions.get("checkvalue")

    defaults: OrderedDict[str, object] = OrderedDict()
    if configure_node is not None:
        evaluator = _ExpressionEvaluator(_build_argument_defaults(configure_node))
        collector = _ConfigureDefaultCollector(evaluator)
        collector.visit(configure_node)
        defaults = collector.defaults

    supported_keys = OrderedDict()
    if checkvalue_node is not None:
        collector = _SupportedKeyCollector()
        collector.visit(checkvalue_node)
        supported_keys = collector.keys

    return OrderedDict(
        (key, defaults[key])
        for key in defaults
        if key in supported_keys and key not in IGNORED_DEFAULT_KEYS and defaults[key] is not None
    )


def extract_runtime_template_path(template_dir_name: str) -> Path | None:
    """Return a stable game-owned config path when the repo or upstream docs declare one."""

    documented = DOCUMENTED_RUNTIME_TEMPLATE_PATHS.get(template_dir_name)
    if documented is not None:
        return documented

    module_path = _resolve_module_path(template_dir_name)
    explicit = _extract_runtime_path_from_module(module_path)
    if explicit is not None:
        return explicit

    doc_name = TEMPLATE_MODULE_ALIASES.get(template_dir_name, template_dir_name)
    canonical_name = MODULE_CATALOG.resolve(doc_name)
    for candidate in (template_dir_name, doc_name, canonical_name):
        if candidate is None:
            continue
        explicit = _extract_runtime_path_from_doc(candidate)
        if explicit is not None:
            return explicit
    return None


def merge_template_defaults(text: str, defaults: OrderedDict[str, object]) -> str:
    """Append missing defaults to an AlphaGSM-oriented example template."""

    missing_lines = [
        f"{key}={format_template_value(value)}"
        for key, value in defaults.items()
        if key not in parse_template_assignments(text)
    ]
    if not missing_lines:
        return text

    base = text.rstrip("\n")
    if base:
        base = base + "\n"
    return base + "\n".join(missing_lines) + "\n"


def format_template_value(value: object) -> str:
    """Render a template value in the repository's simple config style."""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return f'"{value}"'
    if value == "":
        return '""'
    if SIMPLE_STRING_RE.match(value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _build_argument_defaults(function_node: ast.FunctionDef) -> dict[str, object]:
    env: dict[str, object] = {}
    evaluator = _ExpressionEvaluator(env)

    positional_args = function_node.args.args
    positional_defaults = function_node.args.defaults
    if positional_defaults:
        for arg, default in zip(positional_args[-len(positional_defaults):], positional_defaults):
            env[arg.arg] = evaluator.eval(default)

    for arg, default in zip(function_node.args.kwonlyargs, function_node.args.kw_defaults):
        if default is not None:
            env[arg.arg] = evaluator.eval(default)

    return env


def _resolve_module_path(template_dir_name: str) -> Path:
    module_name = TEMPLATE_MODULE_ALIASES.get(template_dir_name, template_dir_name)
    path = MODULE_ROOT.joinpath(*MODULE_CATALOG.resolve(module_name).split(".")).with_suffix(".py")
    if not path.exists():
        raise FileNotFoundError(f"No game module found for template directory {template_dir_name!r}")
    return path


def _extract_runtime_path_from_module(path: Path) -> Path | None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    configure_node = functions.get("configure")
    if configure_node is None:
        return None

    evaluator = _ExpressionEvaluator(_build_argument_defaults(configure_node))
    defaults_collector = _ConfigureDefaultCollector(evaluator)
    defaults_collector.visit(configure_node)
    for key in MODULE_PATH_KEYS:
        value = defaults_collector.defaults.get(key)
        if isinstance(value, str) and value:
            return Path(value)

    for node in ast.walk(configure_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"get", "setdefault"} or len(node.args) < 2:
            continue
        owner = node.func.value
        if not (
            isinstance(owner, ast.Attribute)
            and owner.attr == "data"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "server"
        ):
            continue
        key = evaluator.eval(node.args[0])
        if key not in MODULE_PATH_KEYS:
            continue
        value = evaluator.eval(node.args[1])
        if isinstance(value, str) and value:
            return Path(value)
    return None


def _extract_runtime_path_from_doc(doc_name: str) -> Path | None:
    doc_path = DOCS_ROOT / f"{doc_name}.md"
    if not doc_path.exists():
        return None
    for line in doc_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not CONFIG_LINE_RE.search(line):
            continue
        for match in BACKTICK_RE.findall(line):
            candidate = match.strip()
            if candidate and candidate.lower() != "source":
                return Path(candidate)
    return None


def _read_alias_target(path: Path) -> str | None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != "ALIAS_TARGET":
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    return None
