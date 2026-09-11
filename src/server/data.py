"""This module provides the data store used by servers."""

import os
import json
import copy
from contextlib import contextmanager
from pathlib import Path

from utils.state_io import atomic_write_text, state_lock, sync_directory
from collections.abc import MutableMapping


class DataError(Exception):
    """Thrown when there is an error reading or writing the data store"""

    pass


class JSONDataStore(MutableMapping):
    """Data store that uses json as it's storage engine"""

    def __init__(self, filename, _dict=None):
        """setup the data storeage backed by the file 'filename'.

        If the second optional argument is None or missing then load
        from the file else just used the provided data store.
        """
        self.filename = os.fspath(filename)
        self._transaction_depth = 0
        if _dict is None:
            self._dict = {}
            self.load()
        else:
            self._dict = _dict

    def __len__(self):
        """Get the number of items in the data store"""
        return len(self._dict)

    def __getitem__(self, key):
        """Get the item called 'key'."""
        return self._dict[key]

    def get(self, key, default=None):
        """Get the item called 'key'."""
        return self._dict.get(key, default)

    def __setitem__(self, key, value):
        """Set the item called 'key' to 'value'."""
        self._dict[key] = value

    def __delitem__(self, key):
        """Delete the item called 'key' from this data store."""
        del self._dict[key]

    def __iter__(self):
        """Iterator over the keys in this data store."""
        return iter(self._dict)

    def __contains__(self, item):
        """Check if 'item' is valid key for this data store."""
        return item in self._dict

    def setdefault(self, key, default):
        """If 'key' is not in this data store then set it to 'default'. Return the current value."""
        return self._dict.setdefault(key, default)

    def load(self):
        """Load the data from the data store's file. Completely replaces any current data."""
        with state_lock(self.filename):
            self._recover_pending()
            if not os.path.isfile(self.filename):
                raise DataError("file doesn't exist: " + self.filename)
            with open(self.filename, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if not isinstance(data, dict):
                raise DataError("Expected a JSON object in data store: " + self.filename)
            self._dict = data
            self._load_secrets()

    def _load_secrets(self):
        """Merge the configured secrets file while holding the state lock."""
        secrets_filename = getattr(self, "_secrets_filename", None)
        if secrets_filename and os.path.isfile(secrets_filename):
            with open(secrets_filename, "r", encoding="utf-8") as fp:
                existing = json.load(fp)
            if not isinstance(existing, dict):
                raise DataError("Expected a JSON object in secrets store: " + secrets_filename)
            self._dict.update(existing)

    def set_secret_keys(self, keys, secrets_filename):
        """Configure the existing main/secrets split and load current secrets.

        Secrets stay in an adjacent mode-0600 file. An interrupted paired save is
        recovered from a mode-0600 journal before either file is loaded.
        """
        secrets_filename = os.fspath(secrets_filename)
        reserved_paths = (Path(self.filename).resolve(), self._pending_path,
                          Path(str(Path(self.filename).resolve()) + ".lock"))
        if Path(secrets_filename).resolve() in reserved_paths:
            raise DataError("Secrets require a distinct file from the main data store, journal, and lock.")
        if Path(secrets_filename).resolve().parent != Path(self.filename).resolve().parent:
            raise DataError("Secrets must be stored beside the main data store.")
        self._secret_keys = frozenset(keys)
        self._secrets_filename = secrets_filename
        with state_lock(self.filename):
            self._recover_pending()
            self._load_secrets()

    @contextmanager
    def transaction(self):
        """Reload under a lock, mutate, then save when the outer context exits.

        Nested transactions and explicit saves are deferred until the outer
        context exits. Exceptions from the body restore the in-memory snapshot.
        A failure after the durable paired-save journal is written may be
        completed by the next load; it is not reported as a successful save.
        """
        with state_lock(self.filename):
            outer = self._transaction_depth == 0
            if outer:
                self._recover_pending()
                if os.path.isfile(self.filename):
                    self.load()
            snapshot = copy.deepcopy(self._dict)
            self._transaction_depth += 1
            try:
                yield self
            except BaseException:
                self._dict = snapshot
                raise
            finally:
                self._transaction_depth -= 1
            if outer:
                self.save()

    @property
    def _pending_path(self):
        """Return the sidecar holding an interrupted main/secrets commit."""
        return Path(str(Path(self.filename).resolve()) + ".pending")

    def _recover_pending(self):
        """Complete an interrupted paired save without changing file schemas."""
        pending = self._pending_path
        if not pending.exists():
            return
        with open(pending, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
        if not isinstance(payload, dict):
            raise DataError("Invalid pending state transaction: " + str(pending))
        secret_name = payload.get("secrets_filename")
        if (not isinstance(secret_name, str) or Path(secret_name).name != secret_name
                or secret_name in ("", ".", "..", Path(self.filename).name, pending.name,
                                   Path(self.filename).name + ".lock")
                or not isinstance(payload.get("main"), dict) or not isinstance(payload.get("secrets"), dict)):
            raise DataError("Invalid pending state transaction: " + str(pending))
        atomic_write_text(pending.parent / secret_name, json.dumps(payload["secrets"]), mode=0o600)
        atomic_write_text(self.filename, json.dumps(payload["main"]))
        pending.unlink()
        sync_directory(pending.parent)

    def save(self):
        """Atomically save state, journalling the existing main/secrets split.

        Use transaction() or an outer state_lock() before loading when performing
        a read-modify-write operation; a save-only lock cannot resolve stale data.
        """
        if self._transaction_depth:
            return
        with state_lock(self.filename):
            self._recover_pending()
            if getattr(self, "_secret_keys", None):
                main_dict = {k: v for k, v in self._dict.items() if k not in self._secret_keys}
                secrets_dict = {k: v for k, v in self._dict.items() if k in self._secret_keys}
                payload = {
                    "main": main_dict,
                    "secrets": secrets_dict,
                    "secrets_filename": Path(self._secrets_filename).resolve().name,
                }
                atomic_write_text(self._pending_path, json.dumps(payload), mode=0o600)
                self._recover_pending()
            else:
                atomic_write_text(self.filename, json.dumps(self._dict))

    def prettydump(self):
        """A pretty formated string version of the data for showing to users."""
        secret_keys = getattr(self, "_secret_keys", None)
        if secret_keys:
            display = {
                k: ("<redacted>" if k in secret_keys and v not in (None, "", [], {}, ()) else v)
                for k, v in self._dict.items()
            }
            return json.dumps(display, indent=2, separators=(",", ": "), sort_keys=True)
        return json.dumps(self._dict, indent=2, separators=(",", ": "), sort_keys=True)


__all__ = ["DataError", "JSONDataStore"]
