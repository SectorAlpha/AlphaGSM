"""Static checks for runtime family image contents that must match CI assumptions."""

from pathlib import Path


JAVA_DOCKERFILE = Path("docker/java/Dockerfile")
STEAMCMD_LINUX_DOCKERFILE = Path("docker/steamcmd-linux/Dockerfile")
WINE_PROTON_DOCKERFILE = Path("docker/wine-proton/Dockerfile")
WINE_PROTON_ENTRYPOINT = Path("docker/wine-proton/entrypoint.sh")
BUILD_WORKFLOW = Path(".github/workflows/build-runtime-family-images.yml")


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


def test_steamcmd_linux_runtime_image_keeps_ci_runtime_libraries():
    text = STEAMCMD_LINUX_DOCKERFILE.read_text(encoding="utf-8")

    required_snippets = (
        "lib32gcc-s1",
        "lib32stdc++6",
        "libcurl3t64-gnutls",
        "libatomic1",
        "libsdl2-2.0-0",
        "libpulse0",
        "libssl1.1_1.1.1f-1ubuntu2_amd64.deb",
        "libssl1.0.0_1.0.2n-1ubuntu5_amd64.deb",
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_wine_proton_runtime_image_keeps_ci_wine_and_proton_stack():
    text = WINE_PROTON_DOCKERFILE.read_text(encoding="utf-8")

    required_snippets = (
        "winetricks",
        "wine32:i386",
        "xauth",
        "lib32gcc-s1",
        "lib32stdc++6",
        "libatomic1",
        "libsdl2-2.0-0",
        "libpulse0",
        "wineboot --init",
        "winetricks -q win10",
        "vcrun2019",
        "vcrun2022",
        "wine-mono-8.1.0-x86.msi",
        "install_proton.sh",
        "PROTON_GE_DIR=/opt/proton-ge",
        "ln -s /opt/proton-ge /opt/proton",
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_wine_proton_entrypoint_defaults_to_ci_proton_path():
    text = WINE_PROTON_ENTRYPOINT.read_text(encoding="utf-8")

    assert '/opt/proton-ge/proton' in text


def test_runtime_image_publish_workflow_passes_gh_token_for_proton_builds():
    text = BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert 'secrets:' in text
    assert 'gh_token=${{ secrets.GITHUB_TOKEN }}' in text