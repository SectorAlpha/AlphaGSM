"""Shared, versioned module capability declarations and recorded support evidence.

Runtime hook presence describes an interface, not a successful game-server test.
Missing platform/architecture declarations remain unknown. Discovery never calls
install, configure, start, or container-spec hooks.
"""

from contextlib import redirect_stderr, redirect_stdout
from importlib import import_module
import io
import json
from pathlib import Path
from types import SimpleNamespace

from server.module_catalog import load_default_module_catalog


SCHEMA_VERSION = 1
INVENTORY_PATH = Path(__file__).with_name("module_capabilities.json")
HOOKS = (
    "get_start_command", "get_container_spec", "get_runtime_requirements",
    "get_provider_requirements", "get_query_address", "get_info_address",
    "sync_server_config",
)


def load_capability_inventory(path=None):
    """Read generated capabilities without importing any game modules."""
    path = Path(path) if path is not None else INVENTORY_PATH
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "modules": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("modules"), list):
        raise ValueError("Unsupported module capability inventory schema")
    return payload


def _strings(value):
    """Normalize declared string lists while preserving absent declarations."""
    if value is None:
        return None
    values = [value] if isinstance(value, str) else value
    return sorted({str(item) for item in values})


def _inspect_hook(server, name):
    """Read a metadata hook without leaking its stdout, stderr, or exception text."""
    hook = getattr(server.module, name, None)
    if not callable(hook):
        return None
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            return hook(server)
        except Exception:  # pylint: disable=broad-exception-caught
            return None  # An unconfigured server may not yet have required data.


def get_module_capabilities(server, *, catalog=None, support_state=None):
    """Describe declared interfaces and metadata for a configured or new server."""
    catalog = catalog or load_default_module_catalog()
    module_id = catalog.resolve(server.data.get("module", ""))
    module = server.module
    hooks = {name: callable(getattr(module, name, None)) for name in HOOKS}
    requirements = _inspect_hook(server, "get_runtime_requirements") or {}
    if not isinstance(requirements, dict):
        requirements = {}
    family = requirements.get("family", requirements.get("runtime_family"))
    family = {"minecraft": "java", "ts3": "service-console"}.get(family, family)
    platforms = _strings(getattr(module, "supported_platforms", requirements.get("platforms")))
    architectures = _strings(getattr(module, "supported_architectures", requirements.get("architectures")))
    provider_requirements = _inspect_hook(server, "get_provider_requirements")
    provider_categories = [] if not hooks["get_provider_requirements"] else None
    if isinstance(provider_requirements, (tuple, list)):
        provider_categories = sorted({
            requirement.get("support_category", requirement.get("category"))
            for requirement in provider_requirements
            if requirement.get("support_category", requirement.get("category"))
        })
    protocols = {}
    for kind in ("query", "info"):
        address = _inspect_hook(server, f"get_{kind}_address")
        protocols[kind] = address[2] if isinstance(address, (tuple, list)) and len(address) == 3 else None
    if support_state is None:
        recorded = next((row for row in load_capability_inventory()["modules"]
                         if row["module"] == module_id), {})
        support_state = recorded.get("support_state", "UNKNOWN")
        if recorded.get("provider_categories"):
            provider_categories = sorted(set(provider_categories or ()) | set(recorded["provider_categories"]))
    unknown = [key for key, value in (("platforms", platforms), ("architectures", architectures),
                                     ("runtime.family", family), ("provider_categories", provider_categories))
               if value is None]
    unknown.extend(f"query_protocols.{key}" for key, value in protocols.items() if value is None)
    return {
        "schema_version": SCHEMA_VERSION, "module": module_id,
        "support_state": support_state, "platforms": platforms, "architectures": architectures,
        "runtime": {"process": hooks["get_start_command"],
                    "docker": hooks["get_container_spec"] and hooks["get_runtime_requirements"],
                    "family": family},
        "provider_categories": provider_categories,
        "config_sync_keys": _strings(getattr(module, "config_sync_keys", ())),
        "query_protocols": protocols, "hooks": hooks,
        "unknown_fields": sorted(unknown),
    }


def _canonical_test_id(value, catalog):
    """Resolve documented test names and aliases to canonical module IDs."""
    resolved = catalog.resolve(value)
    if resolved in catalog.canonical_modules:
        return resolved
    dotted = catalog.resolve(value.replace("_", "."))
    return dotted if dotted in catalog.canonical_modules else resolved


def load_support_states(repo_root, catalog):
    """Read tracker evidence, overridden by current explicit support gates."""
    repo_root = Path(repo_root)
    states = {}
    tracker = repo_root / "docs" / "TEST_STATUS.md"
    section = None
    for line in tracker.read_text(encoding="utf-8").splitlines() if tracker.exists() else ():
        if line.startswith("## "):
            section = next((state for state in ("PASSED", "ENABLED (AUTH)", "ENABLED (BYO)", "DISABLED")
                            if line.startswith("## " + state)), None)
        elif section and line.startswith("|"):
            name = _canonical_test_id(line.split("|", 2)[1].strip(), catalog)
            if name in catalog.canonical_modules:
                states[name] = section
    for filename, state in (("enabled_byo_servers.conf", "ENABLED (BYO)"),
                            ("enabled_auth_servers.conf", "ENABLED (AUTH)"),
                            ("disabled_servers.conf", "DISABLED")):
        path = repo_root / filename
        for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else ():
            if line.strip() and not line.lstrip().startswith("#"):
                states[_canonical_test_id(line.split("\t", 1)[0].strip(), catalog)] = state
    return states


def build_capability_inventory(*, catalog, repo_root):
    """Generate declarations for canonical modules without launching game servers."""
    states = load_support_states(repo_root, catalog)
    provider_categories = {}
    auth_path = Path(repo_root) / "enabled_auth_servers.conf"
    for line in auth_path.read_text(encoding="utf-8").splitlines() if auth_path.exists() else ():
        if line.strip() and not line.lstrip().startswith("#"):
            name, category, *_ = line.split("\t")
            provider_categories[_canonical_test_id(name, catalog)] = category
    rows = []
    for module_id in catalog.canonical_modules:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            module = import_module("gamemodules." + module_id)
        server = SimpleNamespace(name="capability-inventory", data={"module": module_id}, module=module)
        row = get_module_capabilities(server, catalog=catalog, support_state=states.get(module_id, "UNKNOWN"))
        if module_id in provider_categories:
            row["provider_categories"] = sorted(set(row["provider_categories"] or ()) | {provider_categories[module_id]})
            row["unknown_fields"] = [key for key in row["unknown_fields"] if key != "provider_categories"]
        row["aliases"] = sorted(alias for alias, target in catalog.aliases.items() if target == module_id)
        rows.append(row)
    return {"schema_version": SCHEMA_VERSION, "modules": rows}
