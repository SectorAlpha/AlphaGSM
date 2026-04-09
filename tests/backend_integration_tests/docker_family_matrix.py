"""Declared Docker backend validation coverage by runtime family."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DockerBackendFamilyCase:
    """Metadata describing one Docker backend validation case."""

    slug: str
    runtime_family: str
    module_name: str
    server_name: str
    validator: str
    status: str
    setup_profile: str
    query_marker: str
    info_marker: str
    info_protocol: str
    notes: str = ""
    default_image: str = ""


DOCKER_BACKEND_FAMILY_CASES = (
    DockerBackendFamilyCase(
        slug="java-minecraft-vanilla",
        runtime_family="java",
        module_name="minecraft.vanilla",
        server_name="bkdocker-vanilla",
        validator="minecraft-status",
        status="active",
        setup_profile="minecraft-vanilla-latest",
        query_marker="Server port is open",
        info_marker="Server info (SLP",
        info_protocol="slp",
        notes="Initial Docker runtime path using the latest vanilla server jar.",
        default_image="eclipse-temurin:25-jre",
    ),
    DockerBackendFamilyCase(
        slug="java-minecraft-paper",
        runtime_family="java",
        module_name="minecraft.paper",
        server_name="bkdocker-paper",
        validator="minecraft-status",
        status="active",
        setup_profile="minecraft-java-listen-port",
        query_marker="Server port is open",
        info_marker="Players     : 0/",
        info_protocol="slp",
        notes="PaperMC server lifecycle using module-managed download resolution.",
        default_image="eclipse-temurin:25-jre",
    ),
    DockerBackendFamilyCase(
        slug="java-minecraft-velocity",
        runtime_family="java",
        module_name="minecraft.velocity",
        server_name="bkdocker-velocity",
        validator="minecraft-status",
        status="active",
        setup_profile="minecraft-java-proxy-port",
        query_marker="Server port is open",
        info_marker="Players     : 0/",
        info_protocol="slp",
        notes="Proxy-style Java runtime coverage via Velocity.",
        default_image="eclipse-temurin:25-jre",
    ),
    DockerBackendFamilyCase(
        slug="quake-linux-q2server",
        runtime_family="quake-linux",
        module_name="q2server",
        server_name="bkdocker-q2",
        validator="quake-query",
        status="planned",
        setup_profile="quake-source-build",
        query_marker="Server is responding",
        info_marker="Players",
        info_protocol="quake",
        notes="Blocked in CI today by source-build toolchain requirements.",
        default_image="ghcr.io/sectoralpha/alphagsm-quake-linux-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="quake-linux-qlserver",
        runtime_family="quake-linux",
        module_name="qlserver",
        server_name="bkdocker-ql",
        validator="quake-query",
        status="planned",
        setup_profile="steamcmd-default",
        query_marker="Server is responding",
        info_marker="Players",
        info_protocol="quake",
        notes="Blocked in CI today because the server exits immediately without extra auth/config.",
        default_image="ghcr.io/sectoralpha/alphagsm-quake-linux-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="quake-linux-etlegacyserver",
        runtime_family="quake-linux",
        module_name="etlegacyserver",
        server_name="bkdocker-etlegacy",
        validator="quake-query",
        status="planned",
        setup_profile="archive-with-game-data",
        query_marker="Server is responding",
        info_marker="Players",
        info_protocol="quake",
        notes="Blocked in CI today because original game data files are required.",
        default_image="ghcr.io/sectoralpha/alphagsm-quake-linux-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="service-console-ts3-default",
        runtime_family="service-console",
        module_name="ts3server",
        server_name="bkdocker-ts3-default",
        validator="tcp-open",
        status="planned",
        setup_profile="ts3-default",
        query_marker="Server is responding",
        info_marker="Clients  :",
        info_protocol="ts3",
        notes="Family currently has one concrete module, so coverage expands via explicit TS3 variants.",
        default_image="ghcr.io/sectoralpha/alphagsm-service-console-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="service-console-ts3-detailed",
        runtime_family="service-console",
        module_name="ts3server",
        server_name="bkdocker-ts3-detailed",
        validator="tcp-open",
        status="planned",
        setup_profile="ts3-detailed-info",
        query_marker="Server is responding",
        info_marker="Clients  :",
        info_protocol="ts3",
        notes="Covers the same module with the detailed-info/query path once the family image is proven.",
        default_image="ghcr.io/sectoralpha/alphagsm-service-console-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="service-console-ts3-alt-ports",
        runtime_family="service-console",
        module_name="ts3server",
        server_name="bkdocker-ts3-ports",
        validator="tcp-open",
        status="planned",
        setup_profile="ts3-alt-ports",
        query_marker="Server is responding",
        info_marker="Clients  :",
        info_protocol="ts3",
        notes="Tracks alternate ServerQuery/file-transfer port wiring in Docker.",
        default_image="ghcr.io/sectoralpha/alphagsm-service-console-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="simple-tcp-mumble-default",
        runtime_family="simple-tcp",
        module_name="mumbleserver",
        server_name="bkdocker-mumble-default",
        validator="tcp-open",
        status="planned",
        setup_profile="mumble-default",
        query_marker="Server port is open",
        info_marker="Server port is open",
        info_protocol="tcp",
        notes="Family currently has one concrete module and still depends on the runtime image replacing host package installs.",
        default_image="ghcr.io/sectoralpha/alphagsm-simple-tcp-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="simple-tcp-mumble-auth",
        runtime_family="simple-tcp",
        module_name="mumbleserver",
        server_name="bkdocker-mumble-auth",
        validator="tcp-open",
        status="planned",
        setup_profile="mumble-auth-config",
        query_marker="Server port is open",
        info_marker="Server port is open",
        info_protocol="tcp",
        notes="Reserved for explicit config-backed Mumble lifecycle validation.",
        default_image="ghcr.io/sectoralpha/alphagsm-simple-tcp-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="simple-tcp-mumble-alt-port",
        runtime_family="simple-tcp",
        module_name="mumbleserver",
        server_name="bkdocker-mumble-port",
        validator="tcp-open",
        status="planned",
        setup_profile="mumble-alt-port",
        query_marker="Server port is open",
        info_marker="Server port is open",
        info_protocol="tcp",
        notes="Reserved for alternate-port Mumble validation once the family image is active.",
        default_image="ghcr.io/sectoralpha/alphagsm-simple-tcp-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="steamcmd-linux-hldmsserver",
        runtime_family="steamcmd-linux",
        module_name="hldmsserver",
        server_name="bkdocker-hldms",
        validator="a2s",
        status="planned",
        setup_profile="steamcmd-default",
        query_marker="Server is responding",
        info_marker="Players     : 0/",
        info_protocol="a2s",
        notes="GoldSrc lifecycle candidate with active non-Docker integration coverage.",
        default_image="ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="steamcmd-linux-cssserver",
        runtime_family="steamcmd-linux",
        module_name="cssserver",
        server_name="bkdocker-css",
        validator="a2s",
        status="planned",
        setup_profile="steamcmd-default",
        query_marker="Server is responding",
        info_marker="Players     : 0/",
        info_protocol="a2s",
        notes="Source-engine lifecycle candidate with active non-Docker integration coverage.",
        default_image="ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="steamcmd-linux-teamfortress2",
        runtime_family="steamcmd-linux",
        module_name="teamfortress2",
        server_name="bkdocker-tf2",
        validator="a2s",
        status="planned",
        setup_profile="steamcmd-source-hibernation-safe",
        query_marker="Server is responding",
        info_marker="Players     : 0/",
        info_protocol="a2s",
        notes="Largest active Source candidate; useful once the family image and hibernation handling are proven.",
        default_image="ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="wine-proton-askaserver",
        runtime_family="wine-proton",
        module_name="askaserver",
        server_name="bkdocker-aska",
        validator="tcp-open",
        status="planned",
        setup_profile="proton-default",
        query_marker="Server is responding",
        info_marker="Players",
        info_protocol="a2s",
        notes="First Windows-on-Linux runtime candidate once the Proton image is CI-ready.",
        default_image="ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="wine-proton-empyrionserver",
        runtime_family="wine-proton",
        module_name="empyrionserver",
        server_name="bkdocker-empyrion",
        validator="tcp-open",
        status="planned",
        setup_profile="proton-default",
        query_marker="Server is responding",
        info_marker="Players",
        info_protocol="a2s",
        notes="Windows dedicated server candidate with existing integration coverage.",
        default_image="ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:2026-04",
    ),
    DockerBackendFamilyCase(
        slug="wine-proton-reignofkingsserver",
        runtime_family="wine-proton",
        module_name="reignofkingsserver",
        server_name="bkdocker-rok",
        validator="tcp-open",
        status="planned",
        setup_profile="proton-default",
        query_marker="Server is responding",
        info_marker="Players",
        info_protocol="a2s",
        notes="Third representative Proton-backed module for future CI enablement.",
        default_image="ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:2026-04",
    ),
)


def all_cases():
    """Return every declared Docker backend family validation case."""

    return DOCKER_BACKEND_FAMILY_CASES


def active_cases():
    """Return the currently enabled Docker backend family cases."""

    return tuple(case for case in DOCKER_BACKEND_FAMILY_CASES if case.status == "active")


def get_case(slug):
    """Return the declared Docker backend case for *slug*."""

    for case in DOCKER_BACKEND_FAMILY_CASES:
        if case.slug == slug:
            return case
    raise KeyError(slug)
