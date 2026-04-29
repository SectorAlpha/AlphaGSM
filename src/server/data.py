"""This module provides the data store used by servers."""

import os
import json
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
        self.filename = filename
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
        if not os.path.isfile(self.filename):
            raise DataError("file doesn't exist: " + self.filename)
        with open(self.filename, "r") as fp:
            data = json.load(fp)
        self._dict = data

    def set_secret_keys(self, keys, secrets_filename):
        """Configure which keys are treated as secrets and their separate file.

        After calling this, ``save()`` will write secret keys exclusively to
        *secrets_filename* (mode 0o600) and keep all other keys in the main
        file, migrating any secret keys currently in the main file on the next
        save.  If *secrets_filename* already exists its contents are merged
        into this store immediately so all keys remain accessible through the
        normal mapping interface.
        """
        self._secret_keys = frozenset(keys)
        self._secrets_filename = secrets_filename
        if os.path.isfile(secrets_filename):
            with open(secrets_filename, "r") as fp:
                existing = json.load(fp)
            self._dict.update(existing)

    def save(self):
        """Save the data to the data store's file."""
        if getattr(self, "_secret_keys", None):
            main_dict = {k: v for k, v in self._dict.items() if k not in self._secret_keys}
            secrets_dict = {k: v for k, v in self._dict.items() if k in self._secret_keys}
            with open(self.filename, "w") as fp:
                json.dump(main_dict, fp)
            fd = os.open(
                self._secrets_filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
            )
            with os.fdopen(fd, "w") as fp:
                json.dump(secrets_dict, fp)
            os.chmod(self._secrets_filename, 0o600)
        else:
            with open(self.filename, "w") as fp:
                json.dump(self._dict, fp)

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
