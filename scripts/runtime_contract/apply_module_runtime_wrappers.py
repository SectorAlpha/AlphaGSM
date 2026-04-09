"""Codemod helpers for inserting explicit runtime wrapper functions."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

import module_family_map


RUNTIME_IMPORT = "import server.runtime as runtime_module"
PROTON_IMPORT = "import utils.proton as proton"
IMPORTLIB_IMPORT = "from importlib import import_module"
ALIAS_MODULE_BINDING = '_ALIAS_MODULE = import_module("gamemodules." + ALIAS_TARGET)'


SHARED_RUNTIME_REQUIREMENTS_TEMPLATE = """def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family={family!r},
        port_definitions={port_definitions!r},
    )
"""


SHARED_CONTAINER_SPEC_TEMPLATE = """def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family={family!r},
        get_start_command=get_start_command,
        port_definitions={port_definitions!r},
        stdin_open={stdin_open!r},
    )
"""

PROTON_RUNTIME_REQUIREMENTS_TEMPLATE = """def get_runtime_requirements(server):
    return proton.get_runtime_requirements(
        server,
        port_definitions={port_definitions!r},
    )
"""


PROTON_CONTAINER_SPEC_TEMPLATE = """def get_container_spec(server):
    return proton.get_container_spec(
        server,
        get_start_command,
        port_definitions={port_definitions!r},
    )
"""


JAVA_RUNTIME_REQUIREMENTS_TEMPLATE = """def get_runtime_requirements(server):
    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    return runtime_module.build_runtime_requirements(
        server,
        family="java",
        port_definitions={port_definitions!r},
        env={{
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
        }},
        extra={{"java": int(java_major)}},
    )
"""


JAVA_CONTAINER_SPEC_TEMPLATE = """def get_container_spec(server):
    requirements = get_runtime_requirements(server)
    return runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=get_start_command,
        port_definitions={port_definitions!r},
        env=requirements.get("env", {{}}),
        stdin_open={stdin_open!r},
    )
"""


ALIAS_RUNTIME_REQUIREMENTS_TEMPLATE = """def get_runtime_requirements(server):
    return _ALIAS_MODULE.get_runtime_requirements(server)
"""


ALIAS_CONTAINER_SPEC_TEMPLATE = """def get_container_spec(server):
    return _ALIAS_MODULE.get_container_spec(server)
"""


def _has_top_level_definition(source, function_name):
    return re.search(
        r"^def %s\(" % (re.escape(function_name),),
        source,
        re.MULTILINE,
    )


def _module_docstring_end_line(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    if not tree.body:
        return None
    first_node = tree.body[0]
    if (
        isinstance(first_node, ast.Expr)
        and isinstance(getattr(first_node, "value", None), ast.Constant)
        and isinstance(first_node.value.value, str)
    ):
        return first_node.end_lineno
    return None


def _find_top_level_insertion_index(lines, source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        insertion_line = _module_docstring_end_line(source)
        return 0 if insertion_line is None else insertion_line

    insertion_line = 0
    for node in tree.body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(getattr(node, "value", None), ast.Constant)
            and isinstance(node.value.value, str)
        ):
            insertion_line = node.end_lineno
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            insertion_line = node.end_lineno
            continue
        break
    return insertion_line


def _ensure_import(source, import_line):
    if import_line in source:
        return source
    lines = source.splitlines()
    index = _find_top_level_insertion_index(lines, source)
    lines.insert(index, import_line)
    if index + 1 >= len(lines) or lines[index + 1].strip():
        lines.insert(index + 1, "")
    return "\n".join(lines) + ("\n" if source.endswith("\n") else "\n")


def _ensure_alias_module_binding(source):
    """Insert the alias module binding after ``ALIAS_TARGET`` when missing."""

    if ALIAS_MODULE_BINDING in source:
        return source
    lines = source.splitlines()
    insert_after = None
    for index, line in enumerate(lines):
        if line.startswith("ALIAS_TARGET"):
            insert_after = index + 1
            break
    if insert_after is None:
        insert_after = _find_top_level_insertion_index(lines, source)
    lines.insert(insert_after, ALIAS_MODULE_BINDING)
    if insert_after + 1 >= len(lines) or lines[insert_after + 1].strip():
        lines.insert(insert_after + 1, "")
    return "\n".join(lines) + ("\n" if source.endswith("\n") else "\n")


def _format_port_definitions(port_definitions):
    normalized = []
    for item in port_definitions or ():
        if isinstance(item, dict):
            normalized.append(dict(item))
        elif isinstance(item, tuple):
            normalized.append(tuple(item))
        else:
            normalized.append(item)
    return tuple(normalized)


def _render_wrapper_snippet(builder, family, port_definitions, stdin_open, function_name):
    if builder == "alias":
        if function_name == "get_runtime_requirements":
            return ALIAS_RUNTIME_REQUIREMENTS_TEMPLATE
        return ALIAS_CONTAINER_SPEC_TEMPLATE
    if builder == "java":
        if function_name == "get_runtime_requirements":
            return JAVA_RUNTIME_REQUIREMENTS_TEMPLATE.format(
                port_definitions=_format_port_definitions(port_definitions),
            )
        return JAVA_CONTAINER_SPEC_TEMPLATE.format(
            port_definitions=_format_port_definitions(port_definitions),
            stdin_open=stdin_open,
        )
    if builder == "proton":
        if function_name == "get_runtime_requirements":
            return PROTON_RUNTIME_REQUIREMENTS_TEMPLATE.format(
                port_definitions=_format_port_definitions(port_definitions),
            )
        return PROTON_CONTAINER_SPEC_TEMPLATE.format(
            port_definitions=_format_port_definitions(port_definitions),
        )
    if function_name == "get_runtime_requirements":
        return SHARED_RUNTIME_REQUIREMENTS_TEMPLATE.format(
            family=family,
            port_definitions=_format_port_definitions(port_definitions),
        )
    return SHARED_CONTAINER_SPEC_TEMPLATE.format(
        family=family,
        port_definitions=_format_port_definitions(port_definitions),
        stdin_open=stdin_open,
    )


def apply_wrappers_to_source(
    source,
    *,
    family=None,
    port_definitions=(),
    stdin_open=True,
    builder="shared",
    module_name=None,
):
    """Insert explicit runtime wrapper functions into *source* if needed."""

    manifest_entry = (
        module_family_map.resolve_module_family(module_name)
        if module_name is not None
        else None
    )
    if manifest_entry is not None:
        family = family or manifest_entry.get("family")
        port_definitions = manifest_entry.get("port_definitions", port_definitions)
        builder = manifest_entry.get("builder", builder)
        stdin_open = manifest_entry.get("stdin_open", stdin_open)
    if family is None:
        raise ValueError("A runtime family is required")

    updated_source = _ensure_import(source, RUNTIME_IMPORT)
    if builder == "proton":
        updated_source = _ensure_import(updated_source, PROTON_IMPORT)
    if builder == "alias":
        updated_source = _ensure_import(updated_source, IMPORTLIB_IMPORT)
        updated_source = _ensure_alias_module_binding(updated_source)

    missing_functions = []
    if not _has_top_level_definition(updated_source, "get_runtime_requirements"):
        missing_functions.append("get_runtime_requirements")
    if not _has_top_level_definition(updated_source, "get_container_spec"):
        missing_functions.append("get_container_spec")

    if not missing_functions:
        return updated_source

    if not updated_source.endswith("\n"):
        updated_source += "\n"
    updated_source = updated_source.rstrip("\n")
    if not updated_source.endswith("\n\n"):
        updated_source += "\n\n"
    wrapper_blocks = [
        _render_wrapper_snippet(
            builder,
            family,
            port_definitions,
            stdin_open,
            function_name,
        ).rstrip("\n")
        for function_name in missing_functions
    ]
    updated_source += "\n\n".join(wrapper_blocks) + "\n"
    return updated_source


def apply_wrappers_to_path(path, *, family=None, module_name=None):
    """Read *path*, apply wrapper insertion, and return the transformed source."""

    source = Path(path).read_text(encoding="utf-8")
    return apply_wrappers_to_source(source, family=family, module_name=module_name)


def _build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Insert explicit runtime wrapper functions into module sources."
    )
    parser.add_argument("path", nargs="+", help="Module file paths to transform")
    parser.add_argument(
        "--family",
        help="Override the runtime family used to generate wrappers",
    )
    parser.add_argument(
        "--module-name",
        help="Resolve wrapper settings from the module-family manifest",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write transformed sources back to disk instead of printing them",
    )
    return parser


def main(argv=None):
    """CLI entry point for the wrapper codemod."""

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    exit_code = 0
    for path_text in args.path:
        path = Path(path_text)
        transformed = apply_wrappers_to_path(
            path,
            family=args.family,
            module_name=args.module_name,
        )
        if args.write:
            path.write_text(transformed, encoding="utf-8")
        else:
            print(transformed, end="" if transformed.endswith("\n") else "\n")
        if not path.exists():
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
