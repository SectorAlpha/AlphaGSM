from abc import ABC as _ABC
from abc import abstractmethod as _abstractmethod
from collections.abc import Sequence as _Sequence
from collections.abc import Callable as _Callable
from typing import Tuple as _Tuple
from typing import Optional as _Optional
from typing import Any as _Any
import sys as _sys


def _identity(s: str) -> str:
    return s


class OptionError(Exception):
    """ An error occurred while parsing the arguments or interpreting the CmdSpec"""

    def __init__(self, msg: str, *args: _Any):
        """Initialise the Exception"""
        self.msg = msg
        self.args = args

    def __str__(self):
        """Convert the Exception to a string"""
        if len(self.args) > 0:
            return "{0}: {1}".format(self.msg, ", ".join(str(a) for a in self.args))
        else:
            return self.msg


class ArgSpec(_Tuple[str, str, _Callable[[str], _Any]]):
    """An argument specification"""

    __slots__ = ()

    def __new__(cls, name: str, description: str, conversion: _Callable[[str], _Any] = _identity) -> 'ArgSpec':
        """Create a new argument specification"""
        return tuple.__new__(cls, (name, description, conversion))

    def __repr__(self):
        """Return a nicely formatted representation string"""
        return 'ArgSpec(name={!r}, description={!r}, conversion={!r})'.format(*self)

    def __getnewargs__(self):
        """Return self as a plain tuple.  Used by copy and pickle."""
        return tuple(self)

    def __getstate__(self):
        """Exclude the OrderedDict from pickling"""
        return None

    @property
    def name(self) -> str:
        """The name of the argument"""
        return self[0]

    @property
    def description(self) -> str:
        """A description for the argument"""
        return self[1]

    @property
    def conversion(self) -> _Callable[[str], _Any]:
        """A function to convert the value to the appropriate type"""
        return self[2]


class OptSpec(_ABC):
    @property
    @_abstractmethod
    def short_forms(self) -> str:
        """The short option names"""
        ...

    @property
    @_abstractmethod
    def long_forms(self) -> _Sequence[str]:
        """The long option names"""
        ...

    @property
    @_abstractmethod
    def description(self) -> str:
        """The description of the option"""
        ...

    @property
    @_abstractmethod
    def keyword(self) -> str:
        """The keyword to store the options result in"""
        ...

    @property
    @_abstractmethod
    def has_argument(self) -> bool:
        """Does this option take an argument"""
        ...

    @property
    @_abstractmethod
    def value(self) -> _Any:
        """The value to store if this option is given. Only valid has_argument is False."""
        ...

    @property
    @_abstractmethod
    def argument(self) -> _Any:
        """The name of the argument to the option. Only valid if has_argument is True."""
        ...

    @property
    @_abstractmethod
    def conversion(self) -> _Callable[[str], _Any]:
        """The function to convert the options argument to the appropriate type. Only valid if has_argument is True."""
        ...


class FlagOptSpec(_Tuple[str, _Sequence[str], str, str, _Any], OptSpec):
    """An option specification"""

    __slots__ = ()

    def __new__(cls, short_forms: str, long_forms: _Sequence[str], description: str, keyword: str,
                value: object = True) -> 'FlagOptSpec':
        """Create a new option specification"""
        return tuple.__new__(cls, (short_forms, long_forms, description, keyword, value))

    def __repr__(self):
        """Return a nicely formatted representation string"""
        return 'FlagOptSpec(short_forms={!r}, long_forms={!r}, description={!r}, keyword={!r}, value={!r})'.format(
            *self)

    def __getnewargs__(self):
        """Return self as a plain tuple.  Used by copy and pickle."""
        return tuple(self)

    def __getstate__(self):
        """Exclude the OrderedDict from pickling"""
        return None

    @property
    def short_forms(self) -> str:
        """The short option names"""
        return self[0]

    @property
    def long_forms(self) -> _Sequence[str]:
        """The long option names"""
        return self[2]

    @property
    def description(self) -> str:
        """The description of the option"""
        return self[2]

    @property
    def keyword(self) -> str:
        """The keyword to store the options result in"""
        return self[3]

    @property
    def has_argument(self) -> bool:
        """Does this option take an argument"""
        return self.argument is not None

    @property
    def value(self) -> _Any:
        """The value to store if this option is given. Only valid has_argument is False."""
        return self[4]

    @property
    def argument(self) -> str:
        """The name of the argument to the option. Only valid if has_argument is True."""
        raise NotImplementedError("Not valid for this flag option")

    @property
    def conversion(self) -> _Callable[[str], _Any]:
        """The function to convert the options argument to the appropriate type. Only valid if has_argument is True."""
        raise NotImplementedError("Not valid for this flag option")


class ArgOptSpec(_Tuple[str, _Sequence[str], str, str, str, _Callable[[str], _Any]], OptSpec):
    """An option specification"""

    __slots__ = ()

    def __new__(cls, short_forms: str, long_forms: _Sequence[str], description: str, keyword: str, argument: str,
                conversion: _Callable[[str], _Any] = _identity) -> 'ArgOptSpec':
        """Create a new option specification"""
        return tuple.__new__(cls, (short_forms, long_forms, description, keyword, argument, conversion))

    def __repr__(self):
        """Return a nicely formatted representation string"""
        return 'ArgOptSpec(short_forms={!r}, long_forms={!r}, description={!r}, keyword={!r}, argument={!r}, ' \
               'conversion={!r})'.format(*self)

    def __getnewargs__(self):
        """Return self as a plain tuple.  Used by copy and pickle."""
        return tuple(self)

    def __getstate__(self):
        """Exclude the OrderedDict from pickling"""
        return None

    @property
    def short_forms(self) -> str:
        """The short option names"""
        return self[0]

    @property
    def long_forms(self) -> _Sequence[str]:
        """The long option names"""
        return self[2]

    @property
    def description(self) -> str:
        """The description of the option"""
        return self[2]

    @property
    def keyword(self) -> str:
        """The keyword to store the options result in"""
        return self[3]

    @property
    def has_argument(self) -> bool:
        """Does this option take an argument"""
        return True

    @property
    def value(self) -> str:
        """The value to store if this option is given. Only valid has_argument is False."""
        raise NotImplementedError("Not valid for this argument option")

    @property
    def argument(self) -> str:
        """The name of the argument to the option. Only valid if has_argument is True."""
        return self[4]

    @property
    def conversion(self) -> _Callable[[str], _Any]:
        """The function to convert the options argument to the appropriate type. Only valid if has_argument is True."""
        return self[5]


class CmdSpec(_Tuple[_Tuple[ArgSpec, ...], _Tuple[ArgSpec, ...], bool, _Tuple[OptSpec, ...]]):
    """A command specification"""

    __slots__ = ()

    def __new__(cls, required_arguments: _Tuple[ArgSpec, ...] = (), optional_arguments: _Tuple[ArgSpec, ...] = (),
                repeatable: bool = False, options: _Tuple[OptSpec, ...] = ()):
        """Create a command specification"""
        return tuple.__new__(cls, (required_arguments, optional_arguments, repeatable, options))

    def __repr__(self):
        """Return a nicely formatted representation string"""
        return 'CmdSpec(required_arguments={!r}, optional_arguments={!r}, repeatable={!r}, options={!r})'.format(*self)

    def __getnewargs__(self):
        """Return self as a plain tuple.  Used by copy and pickle."""
        return tuple(self)

    def __getstate__(self):
        """Exclude the OrderedDict from pickling"""
        return None

    def combine(self, other: _Optional['CmdSpec']):
        """Combine another command spec with this one.

           Ensures that it makes sense to combine the command specifications. i.e. that the first wouldn't already
           absorb all the arguments """
        if other is not None:
            if len(other.required_arguments) > 0:
                raise OptionError("Error combining arguments: Can't add more required arguments")
            if self.repeatable:
                if len(other.optional_arguments) > 0:
                    raise OptionError(
                        "Error combing arguments: Can't add extra arguments, already have a catch all argument")
                return CmdSpec(self.required_arguments, self.optional_arguments, True, self.options + other.options)
            else:
                return CmdSpec(self.required_arguments, self.optional_arguments + other.optional_arguments,
                               other.repeatable, self.options + other.options)
        return self

    @property
    def max_arguments(self):
        """Maximum number of arguments we can take"""
        if self.repeatable:
            return _sys.maxsize
        else:
            return len(self.required_arguments) + len(self.optional_arguments)

    @property
    def min_arguments(self):
        """Minimum number of arguments we can take"""
        return len(self.required_arguments)

    @property
    def has_arguments(self):
        """Are there any arguments"""
        return len(self.required_arguments) > 0 or len(self.optional_arguments) > 0

    @property
    def has_options(self):
        """Are there any arguments"""
        return len(self.options) > 0

    @property
    def required_arguments(self) -> _Tuple[ArgSpec, ...]:
        """The required arguments for the command"""
        return self[0]

    @property
    def optional_arguments(self) -> _Tuple[ArgSpec, ...]:
        """The optional arguments for the command"""
        return self[1]

    @property
    def all_arguments(self) -> _Tuple[ArgSpec, ...]:
        """All the arguments"""
        return self.required_arguments + self.optional_arguments

    @property
    def repeatable(self) -> bool:
        """Is the last argument repeatable"""
        return self[2]

    @property
    def options(self) -> _Tuple[OptSpec, ...]:
        """The options for the command"""
        return self[3]
