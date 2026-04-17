"""Shared helpers for simple key/value config files."""

import os
import re


_EQUALS_PATTERN = re.compile(r"\s*([^ \t\n\r\f\v#]\S*)\s*=(.*?)(\s*)\Z")
_SPACE_PATTERN = re.compile(r"\s*([^ \t\n\r\f\v#]\S*)[ \t\f\v]+(\S*)(\s*)\Z")


def _rewrite_key_value_config(
    filename,
    config_values,
    *,
    pattern,
    separator,
    encoding="utf-8",
):
    lines = []
    if os.path.isfile(filename):
        config_values = config_values.copy()
        with open(filename, "r", encoding=encoding) as handle:
            for line in handle:
                match = pattern.match(line)
                if match is not None and match.group(1) in config_values:
                    lines.append(
                        match.group(1)
                        + separator
                        + str(config_values[match.group(1)])
                        + match.group(3)
                    )
                    del config_values[match.group(1)]
                else:
                    lines.append(line)
    for key, value in config_values.items():
        lines.append("%s%s%s\n" % (key, separator, value))
    with open(filename, "w", encoding=encoding) as handle:
        handle.write("".join(lines))


def rewrite_equals_config(filename, config_values, encoding="utf-8"):
    _rewrite_key_value_config(
        filename,
        config_values,
        pattern=_EQUALS_PATTERN,
        separator="=",
        encoding=encoding,
    )


def rewrite_space_config(filename, config_values, encoding="utf-8"):
    _rewrite_key_value_config(
        filename,
        config_values,
        pattern=_SPACE_PATTERN,
        separator=" ",
        encoding=encoding,
    )
