"""Keep native Windows coverage distinct from Linux platform skips."""

import ast
from configparser import ConfigParser
from pathlib import Path

import yaml


NATIVE_TESTS = {
    "tests/unit_tests/core/test_binary_update.py": {
        "test_wait_for_real_windows_process_exit",
    },
    "tests/unit_tests/screen/test_supervisor_cleanup.py": {
        "test_native_windows_endpoint_reader_can_finish_during_cleanup",
    },
    "tests/unit_tests/screen/test_managed_subprocess.py": {
        "test_windows_job_cleans_descendant_after_parent_exits",
        "test_windows_console_break_reaches_server",
    },
}


def test_native_windows_marker_selects_exactly_the_four_guarded_platform_cases():
    selected = {}
    for filename, expected in NATIVE_TESTS.items():
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"))
        functions = {
            node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        marked = {
            name for name, node in functions.items()
            if any(ast.unparse(mark) == "pytest.mark.native_windows" for mark in node.decorator_list)
        }
        assert marked == expected
        selected[filename] = marked
        for name in marked:
            guards = [mark for mark in functions[name].decorator_list
                      if isinstance(mark, ast.Call) and isinstance(mark.func, ast.Attribute)
                      and mark.func.attr == "skipif"]
            assert len(guards) == 1
            assert isinstance(guards[0].args[0], ast.Compare)
            assert isinstance(guards[0].args[0].ops[0], ast.NotEq)
            assert guards[0].args[0].comparators[0].value == "win32"
    assert sum(map(len, selected.values())) == 4
    config = ConfigParser()
    config.read("pytest.ini", encoding="utf-8")
    assert any(line.strip().startswith("native_windows:")
               for line in config["pytest"]["markers"].splitlines())


def test_windows_native_workflow_runs_real_selected_cases_and_rejects_skips():
    workflow = yaml.load(
        Path(".github/workflows/windows-native-unit.yaml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    assert "workflow_call" in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]
    job = workflow["jobs"]["windows-native-unit"]
    assert job["runs-on"] == "windows-latest"
    assert job["env"]["PYTHONPATH"] == ".;src"
    steps = job["steps"]
    assert any(step.get("uses") == "actions/setup-python@v5"
               and step["with"]["python-version"] == "3.10" for step in steps)
    run = next(step for step in steps if step.get("name") == "Run native Windows unit cases")
    assert "python -m pytest" in run["run"]
    assert "-m native_windows" in run["run"]
    assert "--timeout=60" in run["run"]
    assert "--junitxml=windows-native-unit-results.xml" in run["run"]
    for filename in NATIVE_TESTS:
        assert filename in run["run"]
    guard = next(step for step in steps if step.get("name") == "Require all four native Windows passes")
    assert "sys.platform == 'win32'" in guard["run"]
    assert "len(cases) == 4" in guard["run"]
    assert "'skipped', 'failure', 'error'" in guard["run"]
    for names in NATIVE_TESTS.values():
        for name in names:
            assert name in guard["run"]
    upload = next(step for step in steps if step.get("uses") == "./.github/actions/upload-test-artifact")
    assert upload["if"] == "always()"
    assert upload["with"]["name"] == "windows-native-unit-results-windows"
    assert upload["with"]["path"] == "windows-native-unit-results.xml"
