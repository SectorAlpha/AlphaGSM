"""Immutable configuration objects and config-file loading helpers for AlphaGSM."""

from collections.abc import Mapping
import configparser
import os

_DEFAULT = object()  # unique object to compare identity with


class EmptyMapping(Mapping):
    """A mapping object that always behaves as empty and read-only."""

    def __init__(self, default=None):
        """Initialise the empty mapping with an optional default return value."""
        self._default = default

    def __getitem__(self, key):
        """Always raise because the mapping deliberately contains no keys."""
        raise KeyError("Empty mapping has no contents")

    def __len__(self):
        """Report a length of zero for the empty mapping."""
        return 0

    def __iter__(self):
        """Yield no items because the mapping is empty."""
        while False:
            yield None

    def __contains__(self, key):
        """Report that no key is present in the empty mapping."""
        return False

    def get(self, key, default=_DEFAULT):
        """Return the configured default for any requested key."""
        return self._default if default is _DEFAULT else default

    def __str__(self):
        """Return the string form of an empty mapping."""
        return str({})

    def __repr__(self):
        """Return a debugging representation for the empty mapping."""
        return "<Empty {}>"


class ImmutableMapping(Mapping):
    """A thin immutable mapping wrapper used for loaded settings values."""

    def __init__(self, _dict, default=None):
        """Wrap a concrete dictionary in a read-only mapping interface."""
        self._dict = _dict
        self._default = default

    def __getitem__(self, key):
        """Return the value stored for a key."""
        return self._dict[key]

    def __len__(self):
        """Return the number of entries in the wrapped mapping."""
        return len(self._dict)

    def __iter__(self):
        """Iterate over the keys in the wrapped mapping."""
        yield from self._dict

    def __contains__(self, key):
        """Return whether the wrapped mapping contains the requested key."""
        return key in self._dict

    def get(self, key, default=_DEFAULT):
        """Return the stored value for a key or the configured default."""
        return self._dict.get(key, self._default if default is _DEFAULT else default)

    def __str__(self):
        """Return the string form of the wrapped mapping."""
        return str(self._dict)

    def __repr__(self):
        """Return a debugging representation for the wrapped mapping."""
        return "<Immutable {}>".format(self._dict)


class EmptySection(EmptyMapping):
    """An empty settings section that still exposes section lookup helpers."""

    def __init__(self):
        """Initialise the empty section using the empty-mapping behaviour."""
        super(EmptySection, self).__init__()

    @property
    def sections(self):
        """Get the sections dictionary"""
        return _emptysectiondict

    def getsection(self, key, **kwargs):
        """Return another empty section for any requested subsection."""
        return _emptysection

    def __eq__(self, other):
        """Return whether another section is equal to this empty section."""
        return (
            super(EmptySection, self).__eq__(other) and self.sections == other.sections
        )

    def __str__(self):
        """Return the human-readable form of the empty section."""
        return "<EmptySettings {}>"

    def __repr__(self):
        """Return the debugging representation of the empty section."""
        return "<EmptySettings {}>"


class SettingsSection(ImmutableMapping):
    """A loaded settings section with access to nested subsections."""

    def __init__(self, sections, values):
        """Initialise a section with its child sections and scalar values."""
        super(SettingsSection, self).__init__(values)
        self.__sections = ImmutableMapping(sections, default=_emptysection)

    @property
    def sections(self):
        """Get the sections dictionary"""
        return self.__sections

    def getsection(self, key, **kwargs):
        """Return a named subsection or the configured default section."""
        return self.__sections.get(key, **kwargs)

    def __getattr__(self, name):
        """Allow subsection access via attribute lookup for public names."""
        if name[0] != "_":
            try:
                return self.__sections[name]
            except KeyError:
                pass
        raise AttributeError("'SettingsSection' has no section '{}'".format(name))

    def __eq__(self, other):
        """Return whether another section has the same values and subsections."""
        return (
            super(SettingsSection, self).__eq__(other)
            and self.sections == other.sections
        )

    def __str__(self):
        """Return a readable description of the section contents."""
        return "<Settings {}, subsections: {}>".format(
            self._dict, ", ".join(self.__sections.keys())
        )

    def __repr__(self):
        """Return a debugging representation of the section contents."""
        return "<Settings {}, subsections: {}>".format(self._dict, self.__sections)


_emptysection = EmptySection()
_emptysectiondict = EmptyMapping(default=_emptysection)


def _mergesettings(parent, sectiondict, section, value):
    """Merge one parsed config tree into another, inheriting missing values."""
    for key in parent:
        if key not in value:
            value[key] = parent[key]
    for key in parent.sections:
        if key in sectiondict:
            _mergesettings(parent.sections[key], *sectiondict[key])
        else:
            section[key] = parent.sections[key]


def _loadsettings(filename, parent=None):
    """Load a config file into nested immutable settings-section objects."""
    sectiondicts = {}
    sections = {}
    values = {}
    config = configparser.ConfigParser(
        interpolation=None,
        empty_lines_in_values=False,
        default_section="~#'[&INVALID&]'#~",
        dict_type=dict,
    )

    try:
        with open(filename, "r") as f:
            config.read_file(f)
    except FileNotFoundError as ex:
        if parent is None:
            print("Config file not found")
            raise ex
        else:
            return parent
    except configparser.Error as ex:
        print(ex)
        if parent is None:
            raise ex
        else:
            return parent
    for sectionname in config.sections():
        sectiondict = sectiondicts
        section = sections
        value = values
        for el in sectionname.split("."):
            if el not in sectiondict:
                newsections = {}
                newvalues = {}
                sectiondict[el] = ({}, newsections, newvalues)
                section[el] = SettingsSection(newsections, newvalues)
            sectiondict, section, value = sectiondict[el]
        for key in config[sectionname]:
            value[key] = config[sectionname][key]

    if parent is not None:
        _mergesettings(parent, sectiondicts, sections, values)

    return SettingsSection(sections, values)


def __print(section, indent=""):
    """Render a settings section tree into a human-readable string form."""
    for key, value in section.items():
        print(indent, key, "=", value)
    for key, subsection in section.sections.items():
        print(indent, key, ": {")
        __print(subsection, indent + "  ")
        print(indent, "}")


class Settings(object):
    """Access layered AlphaGSM system and user settings from config files."""

    def __new__(cls):
        """Return the singleton settings object used across the application."""
        try:
            return cls._instance
        except AttributeError:
            cls._instance = super(Settings, cls).__new__(cls)
            return cls._instance

    @property
    def system(self):
        """System settings"""
        try:
            return self._system
        except AttributeError:
            settings_path = os.environ.get(
                "ALPHAGSM_CONFIG_LOCATION",
                (
                    "/etc/alphagsm.conf"
                    if __file__[:5] == "/usr/"
                    else os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "alphagsm.conf",
                    )
                ),
            )
            self._system = _loadsettings(settings_path)
            return self._system

    @property
    def user(self):
        """User settings"""
        try:
            return self._user
        except AttributeError:
            user_settings_path = os.environ.get(
                "ALPHAGSM_USERCONFIG_LOCATION",
                os.path.join(
                    os.path.expanduser(
                        self.system.getsection("core").get("userconf", "~/.alphagsm")
                    ),
                    "alphagsm.conf",
                ),
            )
            self._user = _loadsettings(user_settings_path, self.system)
            return self._user

    def get(self, user):
        """Return the user or system settings tree based on the supplied flag."""
        if user:
            return self.user
        else:
            return self.system


settings = Settings()
