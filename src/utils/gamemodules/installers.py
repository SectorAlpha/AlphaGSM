"""Download operations usable by standard and custom game lifecycle hooks."""


def download_steamcmd(
    server, *, steamcmd_module, steam_app_id,
    steam_anonymous_login_possible, validate=False, download_kwargs=None,
):
    """Download server content, preserving the provider's failure behavior."""
    steamcmd_module.download(
        server.data["dir"], steam_app_id, steam_anonymous_login_possible,
        validate=validate, **dict(download_kwargs or {}),
    )
