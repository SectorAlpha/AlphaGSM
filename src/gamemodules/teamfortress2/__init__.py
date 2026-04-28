"""Package-backed canonical Team Fortress 2 module."""

from . import main as _main
from .layout import ALLOWED_TF2_DESTINATIONS

_PACKAGE_EXPORTS = {}
for _name, _value in _main.__dict__.items():
    if _name.startswith("__") and _name not in {"__doc__"}:
        continue
    _PACKAGE_EXPORTS[_name] = _value
    globals()[_name] = _value

_WRAPPED_FUNCTIONS = (
    "checkvalue",
    "configure",
    "do_stop",
    "get_hibernating_console_info",
    "get_info_address",
    "get_query_address",
    "get_start_command",
    "install",
    "list_setting_values",
    "prestart",
    "status",
    "sync_server_config",
)


def _sync_main_namespace():
    for name, original_value in _PACKAGE_EXPORTS.items():
        if name in _WRAPPED_FUNCTIONS:
            continue
        setattr(_main, name, globals().get(name, original_value))
    _main.ALLOWED_TF2_DESTINATIONS = ALLOWED_TF2_DESTINATIONS


def _wrap_public_function(name):
    target = getattr(_main, name)

    def wrapper(*args, **kwargs):
        _sync_main_namespace()
        return target(*args, **kwargs)

    wrapper.__name__ = target.__name__
    wrapper.__doc__ = target.__doc__
    wrapper.__module__ = __name__
    return wrapper


for _name in _WRAPPED_FUNCTIONS:
    globals()[_name] = _wrap_public_function(_name)

__all__ = sorted(
    {
        *[name for name in _PACKAGE_EXPORTS if not name.startswith("_")],
        "ALLOWED_TF2_DESTINATIONS",
    }
)
