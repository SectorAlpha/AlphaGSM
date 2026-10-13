# pylint: disable=unidiomatic-typecheck
"""Local opt-ins and exact binding policy outside the server datastore namespace."""

from pathlib import Path
import json
import os
import re
from urllib.parse import urlsplit
from utils.state_io import atomic_write_text, state_lock
from .contracts import ACTIONS, identifier, integer, validate_metadata, exact


class ConfigError(ValueError):
    """Invalid local configuration or unsupported permission boundary."""


def origin(value):
    parsed = urlsplit(value)
    invalid = (
        parsed.scheme != "https",
        not parsed.hostname,
        parsed.username,
        parsed.password,
        parsed.path,
        parsed.query,
        parsed.fragment,
    )
    if any(invalid):
        raise ConfigError("Configure one fixed HTTPS origin without credentials or paths")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ConfigError("Invalid HTTPS port")
    return value


def local_tag(value):
    if type(value) is not str or value in (".", "..") or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ConfigError("Select one exact local server tag")
    return value


def default_root():
    from utils.settings import settings

    return Path(os.path.expanduser(settings.user.getsection("core").get("alphagsm_path", "~/.alphagsm"))) / "agent"


class Config:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else default_root()
        if os.name == "nt":
            # POSIX chmod does not establish Windows user-only ACLs. Fail closed
            # until an audited Windows credential-store adapter is supplied.
            raise ConfigError("Remote agent credential storage currently requires POSIX user-only permissions")
        if self.root.is_symlink():
            raise ConfigError("Agent directory must not be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.stat().st_uid != os.getuid():
            raise ConfigError("Agent directory must belong to the current operator")
        os.chmod(self.root, 0o700)
        self.path = self.root / "config.json"
        if self.path.is_symlink():
            raise ConfigError("Agent configuration must not be a symlink")

    def __repr__(self):
        return "Config(<private local agent configuration>)"

    @staticmethod
    def defaults():
        return {
            "schema_version": 1,
            "origin": None,
            "installation_id": None,
            "credential_generation": 0,
            "reporting": None,
            "management": None,
            "reporting_enabled": False,
            "management_enabled": False,
            "policy_version": 1,
            "sequence": 0,
            "bindings": {},
            "dirty_at": 0,
        }

    def load(self):
        if not self.path.exists():
            return self.defaults()
        if self.path.is_symlink() or self.path.stat().st_uid != os.getuid() or self.path.stat().st_mode & 0o077:
            raise ConfigError("Agent configuration must be owned by the operator with mode 0600")
        if self.path.stat().st_size > 256 * 1024:
            raise ConfigError("Agent configuration exceeds size limit")
        value = json.loads(self.path.read_text())
        exact(value, self.defaults())
        if value["schema_version"] != 1:
            raise ConfigError("Unsupported local configuration")
        return value

    def _write(self, value):
        atomic_write_text(self.path, json.dumps(value, sort_keys=True), mode=0o600)

    def enroll(self, api_origin, response):
        origin(api_origin)
        exact(response, ("schema_version", "installation_id", "credential_generation", "reporting", "management"))
        integer(response["schema_version"], 1, 1)
        identifier(response["installation_id"])
        integer(response["credential_generation"])
        for scope in ("reporting", "management"):
            key = response[scope]
            if key is not None:
                exact(key, ("key_id", "secret"))
                identifier(key["key_id"])
                if type(key["secret"]) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{43}", key["secret"]):
                    raise ConfigError("Invalid credential response")
        with state_lock(self.path):
            old = self.load()
            if old["installation_id"] is not None:
                raise ConfigError("Disable and revoke the old relationship before enrolling another provider")
            value = self.defaults()
            value.update(
                {k: response[k] for k in ("installation_id", "credential_generation", "reporting", "management")}
            )
            value["origin"] = api_origin
            self._write(value)

    def replace_credential(self, scope, key_id, secret, *, generation=None):
        """Import one rotated key without granting a capability or changing policy."""
        if scope not in ("reporting", "management"):
            raise ConfigError("Invalid capability")
        identifier(key_id)
        if type(secret) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{43}", secret):
            raise ConfigError("Invalid credential")
        with state_lock(self.path):
            value = self.load()
            if value[scope] is None:
                raise ConfigError("This capability was not enrolled")
            if scope == "management":
                integer(generation)
                if generation <= value["credential_generation"]:
                    raise ConfigError("Management generation must advance")
                value["credential_generation"] = generation
            elif generation is not None:
                raise ConfigError("Reporting rotation does not change management generation")
            value[scope] = {"key_id": key_id, "secret": secret}
            self._write(value)

    def bind(self, binding_id, tag, epoch, *, actions, publication, metadata):
        identifier(binding_id)
        local_tag(tag)
        integer(epoch)
        if (
            type(actions) is not list
            or any(type(a) is not str or a not in ACTIONS for a in actions)
            or len(set(actions)) != len(actions)
        ):
            raise ConfigError("Only status, start, stop and restart are allowed")
        item = {
            "binding_id": binding_id,
            "binding_epoch": epoch,
            "publication": publication,
            "allowed_actions": actions,
            "runtime_state": "unknown",
            **metadata,
        }
        validate_metadata(item)
        with state_lock(self.path):
            value = self.load()
            if len(value["bindings"]) >= 100 and binding_id not in value["bindings"]:
                raise ConfigError("Too many selected bindings")
            if any(b["tag"] == tag and key != binding_id for key, b in value["bindings"].items()):
                raise ConfigError("Only one management binding per local server")
            value["bindings"][binding_id] = {
                "tag": tag,
                "epoch": epoch,
                "actions": actions,
                "publication": publication,
                "metadata": metadata,
            }
            value["policy_version"] += 1
            value["dirty_at"] = __import__("time").time()
            self._write(value)

    def enable(self, *, reporting=None, management=None):
        with state_lock(self.path):
            value = self.load()
            for scope, selection in (("reporting", reporting), ("management", management)):
                if selection is not None:
                    if type(selection) is not bool or (selection and not value[scope]):
                        raise ConfigError("Capability was not enrolled")
                    value[scope + "_enabled"] = selection
            if management is not None:
                value["policy_version"] += 1
            value["dirty_at"] = __import__("time").time()
            self._write(value)

    def unbind(self, binding_id):
        identifier(binding_id)
        with state_lock(self.path):
            value = self.load()
            if binding_id not in value["bindings"]:
                raise ConfigError("Unknown local binding")
            del value["bindings"][binding_id]
            value["policy_version"] += 1
            value["dirty_at"] = __import__("time").time()
            self._write(value)

    def publication(self, binding_id, enabled):
        identifier(binding_id)
        if type(enabled) is not bool:
            raise ConfigError("Publication selection must be boolean")
        with state_lock(self.path):
            value = self.load()
            if binding_id not in value["bindings"]:
                raise ConfigError("Unknown local binding")
            value["bindings"][binding_id]["publication"] = enabled
            value["dirty_at"] = __import__("time").time()
            self._write(value)

    def changed(self):
        with state_lock(self.path):
            value = self.load()
            value["dirty_at"] = __import__("time").time()
            self._write(value)

    def sequence(self):
        with state_lock(self.path):
            value = self.load()
            value["sequence"] += 1
            self._write(value)
            return value

    def forget(self):
        with state_lock(self.path):
            value = self.load()
            if value["management_enabled"] or value["reporting_enabled"]:
                raise ConfigError("Disable both capabilities and revoke centrally before forgetting credentials")
            self._write(self.defaults())
