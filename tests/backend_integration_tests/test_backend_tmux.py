"""Minecraft Vanilla lifecycle test using the tmux backend."""

import pytest

pytestmark = pytest.mark.backend_integration

SERVER_NAME = "bk-tmux"
START_TIMEOUT = 180
STOP_TIMEOUT = 90


def test_minecraft_vanilla_tmux_lifecycle(tmp_path, lifecycle):
    """Full create → setup → start → verify → stop cycle with tmux."""
    lifecycle.require_backend_opt_in()
    lifecycle.require_command("tmux")
    lifecycle.require_command("java")

    home_dir = tmp_path / "alphagsm-home"
    home_dir.mkdir()
    install_dir = tmp_path / "mc-server"
    config_path = tmp_path / "alphagsm.conf"
    java_wrapper = tmp_path / "java-wrapper.sh"

    port = lifecycle.pick_free_tcp_port()
    release_id, server_url = lifecycle.latest_minecraft_release()

    lifecycle.write_config(config_path, home_dir, "BkTmux#", backend="tmux")

    java_wrapper.write_text(
        "#!/usr/bin/env bash\nexec java -Xms256M -Xmx768M \"$@\"\n"
    )
    java_wrapper.chmod(0o755)

    env = lifecycle.alphagsm_env(config_path)

    print(f"Minecraft {release_id}, port {port}, backend=tmux")

    # create & configure
    lifecycle.run_and_assert_ok(env, SERVER_NAME, "create", "minecraft.vanilla")
    lifecycle.run_and_assert_ok(env, SERVER_NAME, "set", "javapath", str(java_wrapper))
    lifecycle.run_and_assert_ok(
        env, SERVER_NAME, "setup", "-n", "-l", str(port),
        str(install_dir), "-u", server_url,
    )

    assert (install_dir / "minecraft_server.jar").exists()
    assert (install_dir / "eula.txt").exists()
    assert (install_dir / "server.properties").exists()

    # start & verify
    lifecycle.run_and_assert_ok(env, SERVER_NAME, "start")
    lifecycle.wait_for_status("127.0.0.1", port, START_TIMEOUT)

    result = lifecycle.run_and_assert_ok(env, SERVER_NAME, "status")
    assert "RUNNING" in (result.stdout + result.stderr).upper() or result.returncode == 0

    lifecycle.run_and_assert_ok(env, SERVER_NAME, "message", "hello from tmux backend")

    # stop
    lifecycle.run_and_assert_ok(env, SERVER_NAME, "stop")
    lifecycle.wait_for_closed("127.0.0.1", port, STOP_TIMEOUT)

    lifecycle.run_and_assert_ok(env, SERVER_NAME, "status")
