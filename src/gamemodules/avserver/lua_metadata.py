"""Read upstream literal modinfo.lua tables without executing downloaded Lua."""

import ast
import re

from server.errors import ServerError

TOKEN = re.compile(r'''\s+|--\[\[.*?\]\]|--[^\n]*|\[\[.*?\]\]|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|\d+(?:\.\d+)?|[{}=,;]''', re.DOTALL)


def parse_metadata(text):
    """Accept literal assignments only; functions and executable tails are refused."""
    tokens, cursor = [], 0
    while cursor < len(text):
        match = TOKEN.match(text, cursor)
        if not match:
            raise ServerError("Avorion modinfo.lua must use supported literal metadata")
        token = match.group()
        cursor = match.end()
        if not token.isspace() and not token.startswith("--"):
            tokens.append(token)
        if len(tokens) > 4096:
            raise ServerError("Avorion metadata exceeds token limit")
    if tokens[:2] == ["meta", "="]:
        del tokens[:2]
    elif tokens[:1] == ["return"]:
        del tokens[:1]
    else:
        raise ServerError("Avorion modinfo.lua needs a literal meta table")
    result, end = _value(tokens, 0, 0)
    if tokens[end:] not in ([], [";"], ["return", "meta"], [";", "return", "meta"]):
        raise ServerError("Executable Avorion metadata is not supported")
    if not isinstance(result, dict):
        raise ServerError("Avorion metadata must be a named table")
    return result


def _value(tokens, index, depth):
    if index >= len(tokens) or depth > 16:
        raise ServerError("Invalid or deeply nested Avorion metadata")
    token = tokens[index]
    if token == "{":
        return _table(tokens, index + 1, depth + 1)
    if token.startswith("[["):
        return token[2:-2], index + 1
    if token.startswith(('"', "'")):
        try:
            return ast.literal_eval(token), index + 1
        except (ValueError, SyntaxError) as exc:
            raise ServerError("Unsupported Avorion metadata string escape") from exc
    if token in ("true", "false"):
        return token == "true", index + 1
    if token[0].isdigit():
        return float(token) if "." in token else int(token), index + 1
    raise ServerError("Avorion metadata values must be literals")


def _table(tokens, index, depth):
    named, array = {}, []
    while index < len(tokens) and tokens[index] != "}":
        key = None
        if index + 1 < len(tokens) and tokens[index + 1] == "=":
            key = tokens[index]
            if not re.fullmatch(r"[A-Za-z_]\w*", key) or key in named:
                raise ServerError("Invalid or duplicate Avorion metadata key")
            index += 2
        value, index = _value(tokens, index, depth)
        if key is None:
            array.append(value)
        else:
            named[key] = value
        if index < len(tokens) and tokens[index] in (",", ";"):
            index += 1
        elif index < len(tokens) and tokens[index] != "}":
            raise ServerError("Invalid Avorion metadata separator")
    if index >= len(tokens) or named and array:
        raise ServerError("Invalid Avorion metadata table")
    return named if named else array, index + 1
