import gamemodules.minecraft.paper as paper
import gamemodules.minecraft.papermc as papermc
import gamemodules.minecraft.velocity as velocity
import gamemodules.minecraft.waterfall as waterfall
import utils.gamemodules.papermc as papermc_impl


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="alpha"):
        self.name = name
        self.data = DummyData()


def test_papermc_resolve_download_chooses_latest_stable_build(monkeypatch):
    responses = {
        "https://fill.papermc.io/v3/projects/paper": {
            "versions": {"stable": ["1.21.10", "1.21.9"]}
        },
        "https://fill.papermc.io/v3/projects/paper/versions/1.21.10/builds": [
            {
                "channel": "EXPERIMENTAL",
                "downloads": {"server:default": {"url": "http://invalid"}},
            },
            {
                "channel": "STABLE",
                "downloads": {"server:default": {"url": "http://example.com/paper.jar"}},
            },
        ],
    }
    monkeypatch.setattr(papermc_impl, "_read_json", lambda url: responses[url])

    version, url = papermc.resolve_download("paper")

    assert version == "1.21.10"
    assert url == "http://example.com/paper.jar"


def test_paper_configure_resolves_download_and_delegates_to_custom(tmp_path, monkeypatch):
    server = DummyServer()
    calls = {}

    monkeypatch.setattr(
        paper,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "http://example.com/paper.jar"),
    )
    monkeypatch.setattr(
        paper.cust,
        "configure",
        lambda server_obj, ask, port, dir, eula=None, exe_name=None: calls.update(
            {"port": port, "dir": dir, "eula": eula, "exe_name": exe_name}
        )
        or ((), {"eula": eula}),
    )

    args, kwargs = paper.configure(server, ask=False, port=25565, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {"eula": None}
    assert server.data["version"] == "1.21.10"
    assert server.data["url"] == "http://example.com/paper.jar"
    assert server.data["download_name"] == "paper.jar"
    assert server.data["mods"]["desired"]["url"] == []
    assert calls["exe_name"] == "paper.jar"


def test_proxy_family_modules_resolve_download_and_delegate_to_bungeecord(
    tmp_path, monkeypatch
):
    velocity_server = DummyServer("velocity")
    waterfall_server = DummyServer("waterfall")
    calls = []

    monkeypatch.setattr(
        velocity,
        "resolve_download",
        lambda project, version=None: ("3.4.0", "http://example.com/velocity.jar"),
    )
    monkeypatch.setattr(
        waterfall,
        "resolve_download",
        lambda project, version=None: ("1.21.10", "http://example.com/waterfall.jar"),
    )
    monkeypatch.setattr(
        velocity.proxy_base,
        "configure",
        lambda server_obj, ask, port=None, dir=None, **kwargs: calls.append(
            (server_obj.name, dir, kwargs)
        )
        or server_obj.data.update(
            {
                "version": kwargs["version"],
                "url": kwargs["url"],
                "download_name": kwargs["download_name"],
                "exe_name": kwargs["exe_name"],
                "mod_cache_dirname": kwargs["mod_cache_dirname"],
                "mod_label": kwargs["mod_label"],
            }
        )
        or ((), {}),
    )

    velocity.configure(velocity_server, ask=False, dir=str(tmp_path / "velocity"))
    waterfall.configure(waterfall_server, ask=False, dir=str(tmp_path / "waterfall"))

    assert (
        "velocity",
        str(tmp_path / "velocity"),
        {
            "version": "3.4.0",
            "url": "http://example.com/velocity.jar",
            "exe_name": "velocity.jar",
            "download_name": "velocity.jar",
            "mod_cache_dirname": "minecraft-velocity",
            "mod_label": "Velocity",
        },
    ) in calls
    assert (
        "waterfall",
        str(tmp_path / "waterfall"),
        {
            "version": "1.21.10",
            "url": "http://example.com/waterfall.jar",
            "exe_name": "waterfall.jar",
            "download_name": "waterfall.jar",
            "mod_cache_dirname": "minecraft-waterfall",
            "mod_label": "Waterfall",
        },
    ) in calls
    assert velocity_server.data["download_name"] == "velocity.jar"
    assert waterfall_server.data["download_name"] == "waterfall.jar"
    assert velocity_server.data["url"] == "http://example.com/velocity.jar"
    assert waterfall_server.data["url"] == "http://example.com/waterfall.jar"
    assert velocity_server.data["mod_cache_dirname"] == "minecraft-velocity"
    assert waterfall_server.data["mod_cache_dirname"] == "minecraft-waterfall"


def test_paper_and_proxy_installs_delegate_to_shared_download_helper(monkeypatch):
    server = DummyServer()
    calls = []

    monkeypatch.setattr(
        paper,
        "install_downloaded_jar",
        lambda server_obj: calls.append(("download", "paper", server_obj)),
    )
    monkeypatch.setattr(
        paper.cust,
        "install",
        lambda server_obj, eula=False: calls.append(("install", "paper", eula)),
    )
    monkeypatch.setattr(
        velocity,
        "install_downloaded_jar",
        lambda server_obj: calls.append(("download", "velocity", server_obj)),
    )
    monkeypatch.setattr(
        velocity.proxy_base,
        "install",
        lambda server_obj, **kwargs: calls.append(
            ("install", server_obj.name, kwargs)
        ),
    )
    monkeypatch.setattr(
        waterfall,
        "install_downloaded_jar",
        lambda server_obj: calls.append(("download", "waterfall", server_obj)),
    )

    paper.install(server, eula=True)
    velocity.install(DummyServer("velocity"))
    waterfall.install(DummyServer("waterfall"))

    assert ("install", "paper", True) in calls
    assert ("install", "velocity", {"configure_listener": False}) in calls
    assert ("install", "waterfall", {}) in calls


def test_velocity_install_does_not_require_bungeecord_config(tmp_path, monkeypatch):
    server = DummyServer("velocity")
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "velocity.jar",
            "download_name": "velocity.jar",
            "url": "https://example.invalid/velocity.jar",
            "current_url": "https://example.invalid/velocity.jar",
            "port": 31234,
        }
    )
    (tmp_path / "velocity.jar").write_text("", encoding="utf-8")

    class FakeProc:
        def __init__(self, *args, **kwargs):
            (tmp_path / "velocity.toml").write_text(
                'bind = "0.0.0.0:25577"\n', encoding="utf-8"
            )

        def poll(self):
            return None

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(velocity.sp, "Popen", FakeProc)
    monkeypatch.setattr(velocity.proxy_base, "_CONFIG_GENERATION_TIMEOUT", 0)

    velocity.install(server)

    assert not (tmp_path / "config.yml").exists()
    assert (tmp_path / "velocity.toml").read_text(encoding="utf-8") == (
        'bind = "0.0.0.0:31234"\n'
    )
