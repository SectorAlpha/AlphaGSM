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


def test_rewrite_equals_config_preserves_literal_backreference_like_value(tmp_path):
    config_path = tmp_path / "server.properties"
    config_path.write_text("motd=Old Name\n", encoding="utf-8")

    rewrite_equals_config(
        str(config_path),
        {"motd": r"\1"},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [r"motd=\1"]


def test_rewrite_space_config_rewrites_single_token_values_and_appends_missing_keys(tmp_path):
    config_path = tmp_path / "server.cfg"
    config_path.write_text(
        "hostname OldName\n"
        "sv_cheats 0\n",
        encoding="utf-8",
    )

    rewrite_space_config(
        str(config_path),
        {"hostname": "NewName", "rcon_password": "secret"},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        "hostname NewName",
        "sv_cheats 0",
        "rcon_password secret",
    ]


def test_rewrite_space_config_appends_quoted_multi_word_duplicate_values(tmp_path):
    config_path = tmp_path / "server.cfg"
    config_path.write_text(
        'hostname "Old Name"\n'
        "sv_cheats 0\n",
        encoding="utf-8",
    )

    rewrite_space_config(
        str(config_path),
        {"hostname": '"New Name"'},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        'hostname "Old Name"',
        "sv_cheats 0",
        'hostname "New Name"',
    ]


def test_rewrite_space_config_leaves_tab_delimited_line_and_appends_new_value(tmp_path):
    config_path = tmp_path / "server.cfg"
    config_path.write_text(
        "hostname\tOldName\n"
        "sv_cheats 0\n",
        encoding="utf-8",
    )

    rewrite_space_config(
        str(config_path),
        {"hostname": "NewName"},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        "hostname\tOldName",
        "sv_cheats 0",
        "hostname NewName",
    ]


def test_rewrite_space_config_rewrites_hash_prefixed_values_in_place(tmp_path):
    config_path = tmp_path / "server.cfg"
    config_path.write_text(
        "rcon_password #placeholder\n"
        "sv_cheats 0\n",
        encoding="utf-8",
    )

    rewrite_space_config(
        str(config_path),
        {"rcon_password": "secret"},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        "rcon_password secret",
        "sv_cheats 0",
    ]


def test_rewrite_space_config_rewrites_mixed_whitespace_boundaries_in_place(tmp_path):
    config_path = tmp_path / "server.cfg"
    config_path.write_text(
        "hostname \tOldName\n"
        "sv_cheats 0\n",
        encoding="utf-8",
    )

    rewrite_space_config(
        str(config_path),
        {"hostname": "NewName"},
    )

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        "hostname NewName",
        "sv_cheats 0",
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
