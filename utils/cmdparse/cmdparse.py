"""Module for parsing arguments using arg_specs and printing usage and help
messages based on CmdSpecs.
"""

import sys as _sys
import textwrap as _textwrap
from collections.abc import Sequence as _Sequence, Generator as _Generator
from itertools import chain as _chain
from typing import Any as _Any, TypeVar as _TypeVar, TextIO as _TextIO, Optional as _Optional,  Dict as _Dict, \
    Tuple as _Tuple

from .cmdspec import OptionError, CmdSpec as _CmdSpec, ArgSpec as _ArgSpec


def parse(in_args: _Sequence[str], cmd_spec: _CmdSpec) -> _Tuple[_Sequence[_Any], _Dict[str, _Any]]:
    """Parse the arguments in 'in_args' according to 'cmd_spec' and return the
    parsed arguments and options."""
    short_options = {}
    long_options = {}
    for i, option in enumerate(cmd_spec.options):
        for c in option.short_forms:
            short_options[c] = i
        for s in option.long_forms:
            long_options[s] = i
    in_args = list(in_args)
    out_args = []
    out_options = {}
    while len(in_args) > 0:  # while still unprocessed arguments
        arg = in_args.pop(0)
        if len(arg) > 0 and arg[0] == "-":  # this argument is an option
            if len(arg) > 1 and arg[1] == "-":  # this argument is a long option
                if arg[2:] not in long_options:
                    raise OptionError("Option '" + arg[2:] + "'not known")
                option = cmd_spec.options[long_options[arg[2:]]]
                if option.has_argument:
                    if len(in_args) < 1:
                        raise OptionError("No argument for option '--" + arg[2:] + "'")
                    try:
                        out_options[option.keyword] = option.conversion(in_args.pop(0))
                    except ValueError as ex:
                        raise OptionError("Argument isn't of the right format for option '--" + arg[2:] + "'", ex)
                else:
                    out_options[option.keyword] = option.value
            else:  # this argument is a short option (or multiple merged short options)
                for c in arg[1:]:
                    if c not in short_options:
                        raise OptionError("Option '" + c + "'not known")
                    option = cmd_spec.options[short_options[c]]
                    if option.has_argument:
                        if len(in_args) < 1:
                            raise OptionError("No argument for option '-" + c + "'")
                        try:
                            out_options[option.keyword] = option.conversion(in_args.pop(0))
                        except ValueError as ex:
                            raise OptionError("Argument isn't of the right format for option '-" + c + "'", ex)
                    else:
                        out_options[option.keyword] = option.value
        else:  # not an option so add it to the args (will check we are allowed an arg here later)
            out_args.append(arg)
    # parsed in_args so check if the out_args for number and then convert them to relevant types
    if len(out_args) < cmd_spec.min_arguments():
        raise OptionError("Not enough arguments provided")
    if (not cmd_spec.repeatable) and len(out_args) > cmd_spec.max_arguments():
        raise OptionError("Too many arguments provided")
    # can always use repeat_last here as we have already checked for the required length
    out_args = [_convert_arg(arg, spec) for arg, spec in zip(out_args, _repeat_last(cmd_spec.all_arguments))]
    # return the parsed arguments and options
    return out_args, out_options


T = _TypeVar('T')


def _repeat_last(a: _Sequence[T]) -> _Generator[T, None, None]:
    """Return an iterator that returns the elements of a then repeats the last
    one forever."""
    last = None
    for el in a:
        last = el  # store in case it is the last argument
        yield el
    if last is None:
        raise ValueError("Empty input isn't supported")
    while True:
        yield last


def _convert_arg(arg: str, spec: _ArgSpec) -> _Any:
    try:
        return spec.conversion(arg)
    except ValueError as ex:
        raise OptionError("Argument isn't of the right format for '" + spec.name + "'", ex)


def short_help(cmd: str, cmd_description: _Optional[str], cmd_spec: _CmdSpec, file: _TextIO = _sys.stderr):
    """Print a short help string for the command based on it's cmd_spec and
    description."""
    s = cmd
    if len(cmd_spec[3]) > 0:
        s += " [OPTION]..."
    for arg in cmd_spec.required_arguments:
        s += " " + arg.name
    for arg in cmd_spec.optional_arguments:
        s += " [" + arg.name + "]"
    if cmd_spec.repeatable:
        s += "..."
    if cmd_description is not None:
        s += " : " + cmd_description.splitlines()[0]
    print(_textwrap.fill(s, 80, initial_indent="  ", subsequent_indent="        "), file=file)


def long_help(cmd: str, cmd_description: _Optional[str], cmd_spec: _CmdSpec, file: _TextIO = _sys.stderr):
    """Print a long help string including the short help, full description and
    descriptions of all the arguments and options."""
    short_help(cmd, None, cmd_spec, file=file)
    print(file=file)
    if cmd_description is not None:
        for par in cmd_description.splitlines():
            print(_textwrap.fill(par, 80), file=file)
            print(file=file)
    if cmd_spec.has_arguments() > 0:
        print("Arguments:", file=file)
        for arg in cmd_spec.all_arguments:
            print(
                _textwrap.fill(arg.name + ": " + arg.description, 80, initial_indent="  ",
                               subsequent_indent="        "),
                file=file)
        print(file=file)
    if cmd_spec.has_options():
        print("Options:", file=file)
        for opt in cmd_spec.options:
            s = ", ".join(_chain(("-" + short for short in opt.short_forms), ("--" + long for long in opt.long_forms)))
            if opt.has_argument:
                s += " " + opt.argument + " "
            s += ": " + opt.description
            print(_textwrap.fill(s, 80, initial_indent="  ", subsequent_indent="        "), file=file)
        print(file=file)
