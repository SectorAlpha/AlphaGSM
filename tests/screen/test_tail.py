import pytest

from tests.helpers import load_module_from_repo


tail_module = load_module_from_repo("screen_tail_module", "screen/tail.py")
tail = tail_module.tail


@pytest.mark.xfail(reason="tail currently uses string.find, which is not available in Python 3")
def test_tail_reads_existing_lines_from_start(tmp_path):
    path = tmp_path / "server.log"
    path.write_text("line one\nline two\n")

    lines = tail(str(path), tailbytes=-1, sleepfor=0)

    assert next(lines) == "line one"
    assert next(lines) == "line two"


@pytest.mark.xfail(reason="tail references fp before assignment when the target file is missing")
def test_tail_missing_file_stops_cleanly(tmp_path):
    lines = tail(str(tmp_path / "missing.log"), sleepfor=0)

    with pytest.raises(StopIteration):
        next(lines)
