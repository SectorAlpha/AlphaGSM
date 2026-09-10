"""Structural validation for explicitly versioned game module interfaces."""

from server.errors import ServerError

REQUIRED_HOOKS = (
    "configure", "install", "get_start_command", "checkvalue", "do_stop",
    "status", "message", "backup", "get_runtime_requirements", "get_container_spec",
)
OPTIONAL_HOOKS = (
    "prestart", "poststart", "postset", "sync_server_config",
    "get_provider_requirements", "get_query_address", "get_info_address",
    "get_platform_requirements", "list_setting_values",
)


def validate_module_contract(module_id, module):
    """Reject malformed versioned declarations without invoking game hooks."""
    version = getattr(module, "module_contract_version", None)
    if version is None:
        return
    # bool subclasses int, so isinstance(True, int) would accept version=True.
    if type(version) is not int or version != 1:  # pylint: disable=unidiomatic-typecheck
        raise ServerError(f"Game module '{module_id}': unsupported contract version")
    issues = []
    for name in REQUIRED_HOOKS:
        if not callable(getattr(module, name, None)):
            issues.append(f"{name} must be a callable public hook")
    for name in OPTIONAL_HOOKS:
        if hasattr(module, name) and not callable(getattr(module, name)):
            issues.append(f"{name} must be callable when declared")
    keys = getattr(module, "config_sync_keys", None)
    if keys is None:
        keys = getattr(module, "set_sync_keys", ())
    if not isinstance(keys, (tuple, list, set, frozenset)) or any(
        not isinstance(key, str) or not key for key in keys
    ):
        issues.append("config_sync_keys must be a collection of nonempty strings")
    elif keys and not callable(getattr(module, "sync_server_config", None)):
        issues.append("config_sync_keys requires sync_server_config")
    if issues:
        raise ServerError(f"Game module '{module_id}': " + "; ".join(issues))
