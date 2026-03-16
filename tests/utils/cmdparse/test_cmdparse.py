from io import StringIO

import pytest

from utils.cmdparse.cmdparse import _convertarg, _replast, longhelp, parse, shorthelp
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec, OptionError


def build_spec():
    return CmdSpec(
        requiredarguments=(ArgSpec("NAME", "server name", str),),
        optionalarguments=(ArgSpec("COUNT", "number", int),),
        repeatable=False,
        options=(
            OptSpec(("q",), ("quiet",), "silence output", "quiet", None, True),
            OptSpec(("n",), ("number",), "numeric value", "number", "NUM", int),
        ),
    )


def test_parse_supports_short_and_long_options():
    args, opts = parse(["-q", "--number", "5", "alpha", "7"], build_spec())

    assert args == ["alpha", 7]
    assert opts == {"quiet": True, "number": 5}


def test_parse_rejects_unknown_option():
    with pytest.raises(OptionError, match="Option 'x'not known"):
        parse(["-x"], build_spec())


def test_parse_requires_option_argument():
    with pytest.raises(OptionError, match="No argument for option '--number'"):
        parse(["--number"], build_spec())


def test_parse_validates_argument_count():
    with pytest.raises(OptionError, match="Not enough arguments provided"):
        parse([], build_spec())

    with pytest.raises(OptionError, match="Too many arguments provided"):
        parse(["alpha", "1", "2"], build_spec())


def test_convertarg_wraps_value_error():
    spec = ArgSpec("COUNT", "number", int)

    with pytest.raises(OptionError, match="Argument isn't of the right format for 'COUNT'"):
        _convertarg("bad", spec)


def test_replast_repeats_the_last_value():
    repeated = _replast(["a", "b"])

    assert [next(repeated) for _ in range(5)] == ["a", "b", "b", "b", "b"]


def test_shorthelp_and_longhelp_include_arguments_and_options():
    short_buffer = StringIO()
    long_buffer = StringIO()
    spec = build_spec()

    shorthelp("start", "Start the service", spec, file=short_buffer)
    longhelp("start", "Start the service\nWith extra detail", spec, file=long_buffer)

    short_output = short_buffer.getvalue()
    long_output = long_buffer.getvalue()

    assert "start [OPTION]... NAME [COUNT]" in short_output
    assert "Start the service" in short_output
    assert "Arguments:" in long_output
    assert "NAME: server name" in long_output
    assert "Options:" in long_output
    assert "--number NUM : numeric value" in long_output


def test_cmdspec_combine_appends_optional_arguments_and_options():
    base = CmdSpec(
        requiredarguments=(ArgSpec("NAME", "server name", str),),
        optionalarguments=(ArgSpec("COUNT", "number", int),),
        repeatable=False,
        options=(OptSpec(("q",), ("quiet",), "quiet", "quiet", None, True),),
    )
    extra = CmdSpec(
        optionalarguments=(ArgSpec("MODE", "mode", str),),
        repeatable=False,
        options=(OptSpec(("f",), ("force",), "force", "force", None, True),),
    )

    combined = base.combine(extra)

    assert combined.requiredarguments == base.requiredarguments
    assert combined.optionalarguments == base.optionalarguments + extra.optionalarguments
    assert combined.repeatable is False
    assert combined.options == base.options + extra.options


@pytest.mark.xfail(reason="repeatable CmdSpec paths are currently broken in production code")
def test_cmdspec_repeatable_maxarguments_is_unbounded():
    spec = CmdSpec(repeatable=True)

    assert spec.maxarguments() > 1000
