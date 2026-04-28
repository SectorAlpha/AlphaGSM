"""Tests for TF2 mod desired-state defaults and command handlers."""

import pytest

import gamemodules.teamfortress2 as tf2
from server import ServerError


class DummyData(dict):
    """Minimal datastore double used by TF2 module tests."""

    def save(self):
        self.saved = True


class DummyServer:
    """Minimal server double used by TF2 module tests."""

    def __init__(self):
        self.name = "tf2mods"
        self.data = DummyData()


def test_configure_seeds_mod_state_defaults(tmp_path):
    server = DummyServer()

    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["mods"]["enabled"] is True
    assert server.data["mods"]["autoapply"] is True
    assert server.data["mods"]["desired"]["curated"] == []
    assert server.data["mods"]["desired"]["workshop"] == []


def test_mod_add_curated_uses_default_channel(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["requested_id"] == "sourcemod"
    assert entry["resolved_id"] == "sourcemod.stable"


def test_mod_add_curated_rejects_duplicate_requested_entry(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")

    with pytest.raises(ServerError, match="already present in desired state"):
        tf2.command_functions["mod"](server, "add", "curated", "sourcemod")


def test_mod_add_curated_accepts_explicit_channel(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "curated", "sourcemod", "1.12")

    entry = server.data["mods"]["desired"]["curated"][0]
    assert entry["resolved_id"] == "sourcemod.1.12"


def test_mod_add_curated_requires_identifier(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="requires a curated family identifier"):
        tf2.command_functions["mod"](server, "add", "curated")


def test_mod_add_curated_rejects_unknown_family_with_server_error(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="Unknown curated mod family: not-a-family"):
        tf2.command_functions["mod"](server, "add", "curated", "not-a-family")


def test_mod_add_curated_rejects_unknown_channel_with_server_error(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="Unknown curated mod release: sourcemod.bad-channel"):
        tf2.command_functions["mod"](server, "add", "curated", "sourcemod", "bad-channel")


def test_mod_add_workshop_accepts_numeric_id_only(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "workshop", "1234567890")
    assert server.data["mods"]["desired"]["workshop"][0]["workshop_id"] == "1234567890"

    with pytest.raises(ServerError, match="numeric workshop id"):
        tf2.command_functions["mod"](server, "add", "workshop", "map_bad")


def test_mod_add_workshop_rejects_duplicate_id(tmp_path):
    server = DummyServer()
    tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    tf2.command_functions["mod"](server, "add", "workshop", "1234567890")

    with pytest.raises(ServerError, match="already present in desired state"):
        tf2.command_functions["mod"](server, "add", "workshop", "1234567890")
