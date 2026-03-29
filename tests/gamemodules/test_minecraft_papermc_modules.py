import gamemodules.minecraft.paper as paper
import gamemodules.minecraft.papermc as papermc
import gamemodules.minecraft.velocity as velocity
import gamemodules.minecraft.waterfall as waterfall


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
    monkeypatch.setattr(papermc, "_read_json", lambda url: responses[url])

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
        lambda server_obj, ask, port=None, dir=None, exe_name=None: calls.append(
            (server_obj.name, dir, exe_name)
        )
        or ((), {}),
    )

    velocity.configure(velocity_server, ask=False, dir=str(tmp_path / "velocity"))
    waterfall.configure(waterfall_server, ask=False, dir=str(tmp_path / "waterfall"))

    assert ("velocity", str(tmp_path / "velocity"), "velocity.jar") in calls
    assert ("waterfall", str(tmp_path / "waterfall"), "waterfall.jar") in calls
    assert velocity_server.data["download_name"] == "velocity.jar"
    assert waterfall_server.data["download_name"] == "waterfall.jar"


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
        lambda server_obj: calls.append(("install", server_obj.name)),
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
    assert ("install", "velocity") in calls
    assert ("install", "waterfall") in calls
