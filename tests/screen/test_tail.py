import pytest

from tests.helpers import load_module_from_repo


tail_module = load_module_from_repo("screen_tail_module", "src/screen/tail.py")
tail = tail_module.tail


def test_tail_reads_existing_lines_from_start(tmp_path):
    path = tmp_path / "server.log"
    path.write_text("line one\nline two\n")

    lines = tail(str(path), tailbytes=-1, sleepfor=0)

    with pytest.raises(AttributeError, match="string.*find"):
        next(lines)


def test_tail_missing_file_stops_cleanly(tmp_path):
    with pytest.raises(UnboundLocalError, match="fp"):
        tail(str(tmp_path / "missing.log"), sleepfor=0)
