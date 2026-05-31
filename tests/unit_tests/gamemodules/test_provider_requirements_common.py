from types import SimpleNamespace

import pytest

from server import ServerError
from utils.gamemodules import common as gamemodule_common


class DummyData(dict):
    pass


def make_server(**data):
    return SimpleNamespace(name="demo", data=DummyData(data))


def test_validate_provider_requirements_raises_for_missing_start_keys():
    server = make_server(eos_client_id="", eos_client_secret="")

    with pytest.raises(ServerError, match="ENABLED \\(AUTH\\)"):
        gamemodule_common.validate_provider_requirements(
            "tiserver",
            server,
            phase="start",
            requirements=[
                {
                    "provider": "eos",
                    "kind": "credential",
                    "keys": ("eos_client_id", "eos_client_secret"),
                    "required_for": ("start",),
                    "support_category": "provider-auth",
                    "summary": "Epic Online Services dedicated-server credentials",
                    "actions": (
                        "Set eos_client_id and eos_client_secret before starting the server",
                    ),
                    "docs_slug": "tiserver",
                }
            ],
        )


def test_validate_provider_requirements_skips_other_phases():
    server = make_server(eos_client_id="", eos_client_secret="")

    gamemodule_common.validate_provider_requirements(
        "tiserver",
        server,
        phase="setup",
        requirements=[
            {
                "provider": "eos",
                "kind": "credential",
                "keys": ("eos_client_id", "eos_client_secret"),
                "required_for": ("start",),
                "support_category": "provider-auth",
                "summary": "Epic Online Services dedicated-server credentials",
                "actions": (
                    "Set eos_client_id and eos_client_secret before starting the server",
                ),
                "docs_slug": "tiserver",
            }
        ],
    )


def test_validate_provider_requirements_raises_when_no_machine_checkable_keys_exist():
    server = make_server()

    with pytest.raises(ServerError, match="ENABLED \\(AUTH\\)"):
        gamemodule_common.validate_provider_requirements(
            "gtafivemserver",
            server,
            phase="start",
            requirements=[
                {
                    "provider": "cfx",
                    "kind": "provisioning",
                    "keys": (),
                    "required_for": ("start",),
                    "support_category": "provider-provisioning",
                    "summary": "txAdmin or vanilla server-data provisioning plus a Cfx license key",
                    "actions": (
                        "Complete txAdmin/server-data provisioning with server.cfg and a Cfx license key before lifecycle validation",
                    ),
                    "docs_slug": "gtafivemserver",
                }
            ],
        )


def test_get_provider_requirements_returns_empty_when_module_has_no_hook():
    module = SimpleNamespace()
    server = make_server()

    assert gamemodule_common.get_provider_requirements(module, server) == []


def test_get_provider_requirements_returns_hook_data():
    module = SimpleNamespace(
        get_provider_requirements=lambda _server: [
            {
                "provider": "eos",
                "kind": "credential",
                "keys": ("eos_client_id", "eos_client_secret"),
                "required_for": ("start",),
                "support_category": "provider-auth",
                "summary": "Epic Online Services dedicated-server credentials",
                "actions": (
                    "Set eos_client_id and eos_client_secret before starting the server",
                ),
                "docs_slug": "tiserver",
            }
        ]
    )
    server = make_server()

    requirements = gamemodule_common.get_provider_requirements(module, server)

    assert requirements[0]["provider"] == "eos"
    assert requirements[0]["docs_slug"] == "tiserver"


def test_format_auth_support_message_includes_actions_and_guide():
    message = gamemodule_common.format_auth_support_message(
        "tiserver",
        "Epic Online Services dedicated-server credentials",
        actions=("Set eos_client_id and eos_client_secret before starting the server",),
        docs_slug="tiserver",
    )

    assert "ENABLED (AUTH): tiserver is supported in AlphaGSM" in message
    assert "Set eos_client_id and eos_client_secret before starting the server." in message
    assert "Guide: docs/servers/tiserver.md." in message
