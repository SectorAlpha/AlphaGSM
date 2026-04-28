"""Tekkit-specific download and startup helpers layered on vanilla Minecraft."""

import os
import urllib.request
import json
import subprocess as sp
from server import ServerError
import re
import screen
import urllib.request
import html5lib
from .vanilla import *
from . import vanilla as van
from utils.cmdparse.cmdspec import CmdSpec, OptSpec, ArgSpec

# path to the download page
import server.runtime as runtime_module

MODPACK_URL_DEFAULT = "https://www.technicpack.net/modpack/tekkitmain.552547"
MODPACK_URL = {
    "tekkit": "https://www.technicpack.net/modpack/tekkitmain.552547",
    "tekkit-legends": "https://www.technicpack.net/modpack/tekkit-legends.735902",
}


def get_file_url(modpack_url):
    """Resolve the direct server download URL from a Tekkit modpack page."""
    try:
        with urllib.request.urlopen(modpack_url) as f:
            dom = html5lib.parse(f, "etree")
    except html5lib.html5parser.ParseError:
        print("WARNING: Error parsing modpack page for download url")
    except urllib.request.URLError:
        print("WARNING: Error downloading modpack page for download url")
    else:
        urls = [
            a.get("href")
            for a in dom.find(dom.tag[:-4] + "body").iter(dom.tag[:-4] + "a")
            if "Server Download" in " ".join(" ".join(a.itertext()).strip().split())
        ]
        if len(urls) >= 1:
            if len(urls) > 1:
                print("WARNING: Multiple download urls found choosing first found.")
            return urls[0]
    return None


command_args = command_args.copy()
command_args["setup"] = CmdSpec(
    optionalarguments=(
        ArgSpec("PORT", "The port for the server to listen on", int),
        ArgSpec("DIR", "The Directory to install minecraft in", str),
    ),
    options=(
        OptSpec(
            "u",
            ["url"],
            "Url to download tekkit from. See https://www.technicpack.net/modpack/tekkitmain.552547 for latest download.",
            "url",
            "URL",
            str,
        ),
        OptSpec(
            "p",
            ["modpack"],
            "Url for the modpack page. Used to locate the latest server url.",
            "modpack_url",
            "URL",
            str,
        ),
    ),
)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    url=None,
    modpack_url=None,
    exe_name="Tekkit.jar",
    download_name="Tekkit.zip"
):
    """Collect and store configuration values for a Tekkit server."""
    if url == None:
        if "url" in server.data and server.data["url"] is not None:
            url = server.data["url"]
        # attempt to find the download url
    if ask or url is None:
        if modpack_url == None:
            if "modpack_url" in server.data and server.data["modpack_url"] is not None:
                modpack_url = server.data["modpack_url"]
        try:
            # get the URL from a known keyword
            modpack_url = MODPACK_URL[modpack_url]
        except KeyError:
            # ok, lets just use this URL anyway
            pass
        server.data["modpack_url"] = modpack_url
        latest_url = get_file_url(modpack_url)
        if url is None:
            url = latest_url
        if ask:
            print(
                "Which url should we use to download tekkit?\nThe latest url is '{}'.".format(
                    latest_url
                )
            )
            inp = input(
                "Please enter the url to download tekkit from or 'latest' for the latest version: [{}] ".format(
                    url
                )
            ).strip()
            if inp != "":
                if inp.lower() == "latest":
                    url = latest_url
                else:
                    url = inp
    if url == None:
        raise ServerError("No download URL available")
    # tekkit run time updates so must have copied of everything so it can update them
    return van.configure(
        server,
        ask,
        port=port,
        dir=dir,
        eula=False,
        version=None,
        url=url,
        exe_name=exe_name,
        download_name=download_name,
        download_data={"linkdir": (), "copy": (r"\.",)},
    )


def get_start_command(server):
    """Build the command list used to launch a Tekkit server."""
    return [
        "java",
        "-Xmx3G",
        "-Xms2G",
        "-jar",
        server.data["exe_name"],
        "nogui",
    ], server.data["dir"]

def get_runtime_requirements(server):
    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    return runtime_module.build_runtime_requirements(
        server,
        family="java",
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env={
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
        },
        extra={"java": int(java_major)},
    )

def get_container_spec(server):
    requirements = get_runtime_requirements(server)
    return runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env=requirements.get("env", {}),
        stdin_open=True,
        tty=True,
    )


def status(server, verbose):
    """Report Tekkit server status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
    return None
