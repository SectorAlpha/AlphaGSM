from utils.simple_kv_config import rewrite_equals_config, rewrite_space_config


def test_rewrite_equals_config_preserves_unknown_lines_and_appends_new_keys(tmp_path):
    config_path = tmp_path / "server.properties"
    config_path.write_text(
        "white-list=false\n"
        "motd=Old Name\n",
        encoding="utf-8",
    )

    rewrite_equals_config(
        str(config_path),
        {"motd": "New Name", "max-players": "20"},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        "white-list=false",
        "motd=New Name",
        "max-players=20",
    ]


def test_rewrite_space_config_preserves_unknown_lines_and_appends_new_keys(tmp_path):
    config_path = tmp_path / "server.cfg"
    config_path.write_text(
        'hostname "Old Name"\n'
        "sv_cheats 0\n",
        encoding="utf-8",
    )

    rewrite_space_config(
        str(config_path),
        {"hostname": '"New Name"', "rcon_password": '"secret"'},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        'hostname "New Name"',
        "sv_cheats 0",
        'rcon_password "secret"',
    ]


def test_rewrite_space_config_rewrites_existing_blank_managed_line(tmp_path):
    config_path = tmp_path / "server.cfg"
    config_path.write_text(
        "rcon_password \n"
        "sv_cheats 0\n",
        encoding="utf-8",
    )

    rewrite_space_config(
        str(config_path),
        {"rcon_password": '"secret"'},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        'rcon_password "secret"',
        "sv_cheats 0",
    ]
