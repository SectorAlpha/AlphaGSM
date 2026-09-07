"""Capabilities describe explicit contracts without claiming unverified support."""

import json
from types import SimpleNamespace

from server import capabilities
from server.module_catalog import ModuleCatalog


def _catalog():
    return ModuleCatalog(("example",), {"alias": "example"}, {})


def test_capabilities_normalize_identity_and_keep_missing_platform_support_unknown():
    server = SimpleNamespace(data={"module": "alias"}, module=SimpleNamespace(
        get_start_command=lambda server: (_ for _ in ()).throw(AssertionError("must not launch")),
    ))
    result = capabilities.get_module_capabilities(server, catalog=_catalog())
    assert result["schema_version"] == 1
    assert result["module"] == "example"
    assert result["platforms"] is None
    assert result["architectures"] is None
    assert result["runtime"] == {"process": True, "docker": False, "family": None}
    assert result["support_state"] == "UNKNOWN"
    assert {"platforms", "architectures", "query_protocols.query"} <= set(result["unknown_fields"])


def test_capabilities_extract_only_declared_metadata_without_installing(capsys):
    def requirements(_server):
        print("must not leak into doctor JSON")
        return {"family": "java", "engine": "docker"}

    def forbidden(*_args):
        raise AssertionError("Capability discovery must not install or start a server")

    module = SimpleNamespace(
        supported_platforms=("linux", "windows"), supported_architectures=("x86_64",),
        get_runtime_requirements=requirements, get_container_spec=forbidden,
        get_start_command=forbidden, install=forbidden, configure=forbidden,
        get_provider_requirements=lambda server: [{"category": "provider-token", "keys": ["secret"]}],
        config_sync_keys=("port", "servername"),
        get_query_address=lambda server: ("localhost", 1, "tcp"),
        get_info_address=lambda server: ("localhost", 1, "slp"),
    )
    server = SimpleNamespace(data={"module": "example", "secret": "must-not-leak"}, module=module)
    result = capabilities.get_module_capabilities(server, catalog=_catalog())
    assert result["runtime"] == {"process": True, "docker": True, "family": "java"}
    assert result["provider_categories"] == ["provider-token"]
    assert result["platforms"] == ["linux", "windows"]
    assert result["architectures"] == ["x86_64"]
    assert result["config_sync_keys"] == ["port", "servername"]
    assert result["query_protocols"] == {"query": "tcp", "info": "slp"}
    assert "must-not-leak" not in json.dumps(result)
    assert not capsys.readouterr().out


def test_failed_unconfigured_hooks_produce_unknown_fields_without_secret_errors():
    def missing(server):
        raise ValueError("credentials=must-not-leak")
    server = SimpleNamespace(data={"module": "example"}, module=SimpleNamespace(
        get_runtime_requirements=missing, get_provider_requirements=missing,
        get_info_address=missing,
    ))
    result = capabilities.get_module_capabilities(server, catalog=_catalog())
    assert result["runtime"]["family"] is None
    assert result["provider_categories"] is None
    assert result["query_protocols"]["info"] is None
    assert "must-not-leak" not in json.dumps(result)


def test_support_states_require_recorded_evidence_instead_of_non_disabled_guess(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "TEST_STATUS.md").write_text("## PASSED (1)\n| alias | verified |\n")
    assert capabilities.load_support_states(tmp_path, _catalog()) == {"example": "PASSED"}
    (tmp_path / "enabled_auth_servers.conf").write_text("alias\tprovider-token\tRequires token\n")
    assert capabilities.load_support_states(tmp_path, _catalog()) == {"example": "ENABLED (AUTH)"}
    (tmp_path / "disabled_servers.conf").write_text("alias\tunsupported\n")
    assert capabilities.load_support_states(tmp_path, _catalog()) == {"example": "DISABLED"}


def test_capability_inventory_loads_without_importing_game_modules(tmp_path, monkeypatch):
    path = tmp_path / "capabilities.json"
    path.write_text(json.dumps({"schema_version": 1, "modules": [{"module": "example"}]}))
    monkeypatch.setattr(capabilities, "import_module", lambda name: (_ for _ in ()).throw(AssertionError(name)))
    assert capabilities.load_capability_inventory(path)["modules"] == [{"module": "example"}]
