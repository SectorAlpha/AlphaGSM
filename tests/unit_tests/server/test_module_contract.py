from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from server.errors import ServerError
from server.module_contract import validate_module_contract


HOOK_NAMES = (
    "configure", "install", "get_start_command", "checkvalue", "do_stop",
    "status", "message", "backup", "get_runtime_requirements", "get_container_spec",
)


def valid_module():
    return SimpleNamespace(
        module_contract_version=1,
        **{name: Mock() for name in HOOK_NAMES},
    )


def test_legacy_modules_remain_compatible():
    validate_module_contract("legacy", SimpleNamespace())


def test_inspection_does_not_execute_hooks():
    module = valid_module()
    validate_module_contract("demo", module)
    for name in HOOK_NAMES:
        getattr(module, name).assert_not_called()


@pytest.mark.parametrize("name", HOOK_NAMES)
def test_missing_hook_names_the_module_and_hook(name):
    module = valid_module()
    delattr(module, name)
    with pytest.raises(ServerError, match="demo.*" + name):
        validate_module_contract("demo", module)


@pytest.mark.parametrize("keys", ["port", [1], {"port": True}])
def test_sync_keys_require_a_collection_of_strings(keys):
    module = valid_module()
    module.config_sync_keys = keys
    module.sync_server_config = Mock()
    with pytest.raises(ServerError, match="config_sync_keys"):
        validate_module_contract("demo", module)


def test_nonempty_sync_keys_require_a_sync_hook():
    module = valid_module()
    module.config_sync_keys = ("port",)
    with pytest.raises(ServerError, match="sync_server_config"):
        validate_module_contract("demo", module)


def test_unknown_contract_version_is_actionable():
    with pytest.raises(ServerError, match="demo.*version"):
        validate_module_contract("demo", SimpleNamespace(module_contract_version=2))


def test_boolean_contract_version_is_actionable():
    with pytest.raises(ServerError, match="demo.*version"):
        validate_module_contract("demo", SimpleNamespace(module_contract_version=True))


@pytest.mark.parametrize("name", (
    "prestart", "poststart", "postset", "sync_server_config",
    "get_provider_requirements", "get_query_address", "get_info_address",
    "get_platform_requirements", "list_setting_values",
))
def test_declared_optional_hooks_must_be_callable(name):
    module = valid_module()
    setattr(module, name, "not-callable")
    with pytest.raises(ServerError, match="demo.*" + name):
        validate_module_contract("demo", module)


@pytest.mark.parametrize("keys", [(), [], set(), frozenset()])
def test_empty_sync_keys_do_not_require_a_sync_hook(keys):
    module = valid_module()
    module.config_sync_keys = keys
    validate_module_contract("demo", module)


def test_legacy_set_sync_keys_are_validated():
    module = valid_module()
    module.set_sync_keys = ("port",)
    with pytest.raises(ServerError, match="sync_server_config"):
        validate_module_contract("demo", module)
    module.sync_server_config = Mock()
    validate_module_contract("demo", module)


def test_loader_validates_before_runtime_inference(monkeypatch):
    from server import server as server_module

    module = SimpleNamespace(module_contract_version=1)
    infer = Mock()
    monkeypatch.setattr(server_module, "_load_disabled_servers", lambda: {})
    monkeypatch.setattr(server_module, "import_module", lambda _name: module)
    monkeypatch.setattr(server_module.runtime_module, "ensure_runtime_hooks", infer)
    with pytest.raises(ServerError, match="palworld.*configure"):
        server_module.find_module("palworld")
    infer.assert_not_called()
