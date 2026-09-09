"""Static checks for runtime family image contents that must match CI assumptions."""

from pathlib import Path


JAVA_DOCKERFILE = Path("docker/java/Dockerfile")
QUAKE_LINUX_DOCKERFILE = Path("docker/quake-linux/Dockerfile")
SIMPLE_TCP_DOCKERFILE = Path("docker/simple-tcp/Dockerfile")
STEAMCMD_LINUX_DOCKERFILE = Path("docker/steamcmd-linux/Dockerfile")
WINE_PROTON_DOCKERFILE = Path("docker/wine-proton/Dockerfile")
WINE_PROTON_ENTRYPOINT = Path("docker/wine-proton/entrypoint.sh")
BUILD_WORKFLOW = Path(".github/workflows/build-runtime-family-images.yml")
MANUAL_INTEGRATION_BUILD_WORKFLOW = Path(
    ".github/workflows/build-integration-image.yml"
)
DOCKER_README = Path("docker/README.md")
INTEGRATION_ENV_DOCKERFILE = Path(".github/docker/integration-env/Dockerfile")
PR_WORKFLOW = Path(".github/workflows/unittest.yaml")


def test_java_runtime_image_keeps_bootstrap_tools_and_supported_temurin_jres():
    text = JAVA_DOCKERFILE.read_text(encoding="utf-8")

    required_snippets = (
        "wget -q -O /usr/share/keyrings/adoptium.asc",
        "wget",
        "temurin-17-jre",
        "temurin-21-jre",
        "temurin-25-jre",
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_java_runtime_image_uses_utf8_for_native_unicode_cache_paths():
    """Java's file.encoding alone does not control canonical jar path decoding."""
    text = JAVA_DOCKERFILE.read_text(encoding="utf-8")
    environment = {}
    for line in text.replace("\\\n", " ").splitlines():
        if line.startswith("ENV "):
            environment.update(item.split("=", 1) for item in line[4:].split())

    assert environment.get("LANG") == "C.UTF-8"
    assert environment.get("LC_ALL") == "C.UTF-8"


def test_quake_linux_runtime_keeps_quakeworld_libcurl_available():
    text = QUAKE_LINUX_DOCKERFILE.read_text(encoding="utf-8")

    assert "libcurl4t64" in text


def test_steamcmd_linux_runtime_image_keeps_ci_runtime_libraries():
    text = STEAMCMD_LINUX_DOCKERFILE.read_text(encoding="utf-8")

    required_snippets = (
        "lib32gcc-s1",
        "lib32stdc++6",
        "libcurl3t64-gnutls",
        "libcurl4-gnutls-dev",
        "libcurl3t64-gnutls:i386",
        "libx11-6:i386",
        "ln -sf libcurl.so.4 /usr/lib/i386-linux-gnu/libcurl.so",
        "libatomic1",
        "libsdl2-2.0-0",
        "libpulse0",
        "libpulse-dev",
        "libssl1.1_1.1.1f-1ubuntu2_amd64.deb",
        "libssl1.0.0_1.0.2n-1ubuntu5_amd64.deb",
        "packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb",
        "dotnet-runtime-10.0",
        "dotnet-install.sh",
        "--channel 6.0",
        "--install-dir /usr/lib/dotnet",
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_integration_image_keeps_official_valheim_linux_packages_across_layers():
    text = "\n".join(
        (
            WINE_PROTON_DOCKERFILE.read_text(encoding="utf-8"),
            INTEGRATION_ENV_DOCKERFILE.read_text(encoding="utf-8"),
        )
    )

    required_snippets = (
        "libatomic1",
        "libstdc++5:i386",
        "libpulse0",
        "libpulse-dev",
        "libcurl4-gnutls-dev",
        "libcurl3t64-gnutls:i386",
        "ln -sf libcurl.so.4 /usr/lib/i386-linux-gnu/libcurl.so",
    )
    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_integration_image_includes_dotnet6_for_legacy_linux_servers():
    text = INTEGRATION_ENV_DOCKERFILE.read_text(encoding="utf-8")

    required_snippets = (
        "dotnet-install.sh",
        "--channel 6.0",
        "--install-dir /usr/lib/dotnet",
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_simple_tcp_runtime_image_keeps_mumble_service_binary_available():
    text = SIMPLE_TCP_DOCKERFILE.read_text(encoding="utf-8")

    required_snippets = (
        "bash",
        "python3",
        "mumble-server",
        "ln -s /usr/sbin/murmurd /usr/local/bin/mumble-server",
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_wine_proton_runtime_image_keeps_ci_wine_and_proton_stack():
    text = WINE_PROTON_DOCKERFILE.read_text(encoding="utf-8")

    required_snippets = (
        "winetricks",
        "wine32:i386",
        "xauth",
        "fontconfig",
        "lib32gcc-s1",
        "lib32stdc++6",
        "libatomic1",
        "libgdiplus",
        "libsdl2-2.0-0",
        "libpulse0",
        "wineboot --init",
        "winetricks -q win10",
        "corefonts",
        "vcrun2019",
        "vcrun2022",
        "wine-mono-8.1.0-x86.msi",
        "install_proton.sh",
        "PROTON_GE_DIR=/opt/proton-ge",
        "ln -s /opt/proton-ge /opt/proton",
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_wine_proton_runtime_installs_vcrun_with_a_display_and_fails_closed():
    text = WINE_PROTON_DOCKERFILE.read_text(encoding="utf-8")

    assert "Xvfb :99" in text
    assert "export DISPLAY=:99" in text
    assert "export WINEDLLOVERRIDES=" in text
    assert "winetricks -q --force vcrun2019 || true" not in text
    assert "winetricks -q --force vcrun2022 || true" not in text


def test_proton_images_copy_architecture_asset_selector():
    text = WINE_PROTON_DOCKERFILE.read_text(encoding="utf-8")

    assert (
        "COPY scripts/select_proton_asset.py /tmp/select_proton_asset.py"
        in text
    )


def test_integration_image_reuses_wine_proton_runtime_layers():
    text = INTEGRATION_ENV_DOCKERFILE.read_text(encoding="utf-8")

    assert text.startswith(
        "ARG WINE_PROTON_IMAGE="
        "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest\n"
        "FROM ${WINE_PROTON_IMAGE}\n"
    )
    assert "COPY scripts/install_proton.sh" not in text
    assert "wineboot --init" not in text
    assert "wine-mono-8.1.0-x86.msi" not in text


def test_proton_image_cache_keys_include_architecture_asset_selector():
    for workflow in (PR_WORKFLOW, MANUAL_INTEGRATION_BUILD_WORKFLOW):
        text = workflow.read_text(encoding="utf-8")

        assert "scripts/select_proton_asset.py" in text


def test_wine_proton_entrypoint_defaults_to_ci_proton_path():
    text = WINE_PROTON_ENTRYPOINT.read_text(encoding="utf-8")

    assert '/opt/proton-ge/proton' in text


def test_wine_proton_entrypoint_bootstraps_xdg_runtime_dir_for_xvfb_servers():
    text = WINE_PROTON_ENTRYPOINT.read_text(encoding="utf-8")

    assert 'ensure_xdg_runtime_dir()' in text
    assert 'XDG_RUNTIME_DIR="/tmp/alphagsm-xdg-runtime"' in text
    assert 'chmod 700 "${XDG_RUNTIME_DIR}"' in text


def test_runtime_image_publish_workflow_passes_gh_token_for_proton_builds():
    text = BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert 'secrets:' in text
    assert 'gh_token=${{ secrets.GITHUB_TOKEN }}' in text


def test_pr_workflow_passes_github_token_to_download_validation_jobs():
    text = PR_WORKFLOW.read_text(encoding="utf-8")

    assert text.count(
        "ALPHAGSM_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}"
    ) >= 4
    assert text.count(
        "export ALPHAGSM_GITHUB_TOKEN='${ALPHAGSM_GITHUB_TOKEN}'"
    ) >= 2


def test_runtime_image_publish_workflow_links_packages_back_to_repo():
    text = BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert "labels:" in text
    assert "org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}" in text


def test_runtime_image_publish_workflow_avoids_unsupported_visibility_patch_api():
    text = BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert "Set package visibility to public" not in text
    assert "/packages/container/${package_name}" not in text
    assert "--field visibility=public" not in text


def test_runtime_image_docs_default_to_latest_tags():
    text = DOCKER_README.read_text(encoding="utf-8")

    assert "alphagsm-java-runtime:latest" in text
    assert "docker/image-version.txt" not in text


def test_integration_image_gives_gsmuser_write_access_to_wine_and_proton_trees():
    text = INTEGRATION_ENV_DOCKERFILE.read_text(encoding="utf-8")

    assert "chown -R gsmuser:gsmuser /opt/wine /opt/proton-ge" in text


def test_pr_integration_image_build_uses_branch_local_wine_proton_base():
    text = PR_WORKFLOW.read_text(encoding="utf-8")
    section = text.split("  build-integration-image:")[1].split(
        "  build-steamcmd-linux-runtime:"
    )[0]

    assert (
        "needs: [unit-test, lint, coverage, build-wine-proton-runtime]"
        in section
    )
    assert (
        "WINE_PROTON_IMAGE=${{ needs.build-wine-proton-runtime.outputs.image }}"
        in section
    )
    assert (
        "wine_proton_image='${{ needs.build-wine-proton-runtime.outputs.image }}'"
        in section
    )


def test_manual_integration_image_build_builds_and_reuses_wine_proton_base():
    text = MANUAL_INTEGRATION_BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert "Build and push wine-proton runtime image" in text
    assert "file: docker/wine-proton/Dockerfile" in text
    assert "WINE_PROTON_IMAGE=${{ steps.meta.outputs.wine_image }}" in text
