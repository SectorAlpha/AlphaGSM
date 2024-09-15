import pytest
from time import sleep, time
from unittest.mock import Mock, MagicMock, patch
import subprocess as sp
import selectors
from io import BytesIO
from multiprocessing import Process, Queue
from core.multiplexer import Multiplexer, StreamData, OutputInteruptedException, addtomultiafter

# Mock classes
class MockProc:
    def __init__(self, stdout=None, stderr=None, returncode=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def poll(self):
        return self.returncode

    def wait(self):
        return self.returncode

    def communicate(self):
        return (self.stdout.read(), self.stderr.read())

class MockStream:
    def __init__(self, data):
        self.data = BytesIO(data)

    def read1(self, n):
        return self.data.read(n)

    def close(self):
        pass

    def fileno(self):
        return 1

@pytest.fixture
def multiplexer(mock_selector):
    # Initialize Multiplexer with the mocked selector
    return Multiplexer()

@pytest.fixture
def mock_selector():
    with patch('selectors.DefaultSelector') as MockSelector:
        mock_selector_instance = MockSelector.return_value
        yield mock_selector_instance

@pytest.fixture
def mock_popen(monkeypatch):
    mock_popen = MagicMock()
    monkeypatch.setattr(sp, "Popen", mock_popen)
    return mock_popen


def long_running_process(queue):
    """Function to simulate a long-running process that outputs periodically."""
    for i in range(5):
        print(f"Iteration {i}")
        time.sleep(1)
    queue.put("done")


def test_multiplexer(mock_selector):
    # Mock process with stdout and stderr streams
    proc = MockProc(stdout=MockStream(b"output"), stderr=MockStream(b"error"))

    with patch('selectors.DefaultSelector', return_value=mock_selector):
        mux = Multiplexer()

        # Add the mocked process to the multiplexer
        mux.addproc("test", proc)

        # Simulate a selector event by providing an empty list return
        mock_selector.select.return_value = []

        # Call the process method, which should invoke select on the selector
        result = mux.process()

        # Validate that the process method handled the empty selector correctly
        assert result is not None

        # Ensure that the select method was called exactly once
        mock_selector.select.assert_called_once_with(None)

def test_addproc(multiplexer):
    proc = MockProc(stdout=MockStream(b"output"), stderr=MockStream(b"error"))
    multiplexer.addproc("test", proc)

    assert proc in multiplexer.procs
    assert multiplexer.streams[proc.stdout].tag is None
    assert multiplexer.streams[proc.stderr].tag is None
    assert len(multiplexer.streamlessprocs) == 0

def test_removestream(multiplexer):
    stream = MockStream(b"output")
    proc = MockProc(stdout=stream)
    multiplexer.addproc("test", proc)

    multiplexer.removestream(stream)

    assert stream not in multiplexer.streams
    assert proc in multiplexer.streamlessprocs


def test_removeproc(multiplexer):
    # Create a MockStream and a MockProc with the stream as stdout
    stream = MockStream(b"output")
    proc = MockProc(stdout=stream)

    # Add the process to the multiplexer
    multiplexer.addproc("test", proc)

    # Ensure the process and its stream are in the multiplexer
    assert proc in multiplexer.procs
    assert stream in multiplexer.streams

    # Remove the process
    multiplexer.removeproc(proc)

    # Validate that the process and its associated stream are removed
    assert proc not in multiplexer.procs
    assert proc not in multiplexer.streamlessprocs
    assert stream not in multiplexer.streams


def test_addtomultiafter():
    multi = Multiplexer()

    def linecheck(line):
        return b"stop" in line

    with patch("builtins.print") as mocked_print:
        addtomultiafter(multi, "test", linecheck, ["echo", "test"])
        assert mocked_print.called

    assert len(multi.procs) == 0  # Ensure no processes are left after running


def test_run_process(mock_popen, multiplexer):
    mock_proc = MockProc(stdout=MockStream(b"output\n"))
    mock_popen.return_value = mock_proc

    multiplexer.run("test", ["echo", "test"])

    assert mock_proc in multiplexer.procs
    assert multiplexer.streams[mock_proc.stdout].tag is None
    assert len(multiplexer.streamlessprocs) == 0


def test_addbareproc_existing_proc(multiplexer):
    proc = MockProc(stdout=MockStream(b"output"))
    multiplexer.addbareproc("test1", proc)
    multiplexer.addbareproc("test2", proc)  # Tag should be updated

    assert multiplexer.procs[proc].tag == "test2"


def test_addstream_with_data(multiplexer):
    stream = MockStream(b"initial_data")
    proc = MockProc(stdout=stream)
    multiplexer.addbareproc("test", proc)

    multiplexer.addstream(stream, proc, data=b"initial_data")

    assert stream in multiplexer.streams
    assert stream in multiplexer.checkdata

def test_addstream_with_different_data_error(multiplexer):
    stream = MockStream(b"initial_data")
    proc = MockProc(stdout=stream)
    multiplexer.addbareproc("test", proc)

    multiplexer.addstream(stream, proc, data=b"initial_data")

    with pytest.raises(ValueError):
        multiplexer.addstream(stream, proc, data=b"different_data")


def test_transfer(multiplexer):
    proc = MockProc(stdout=MockStream(b"output"))
    multiplexer.addproc("test", proc)

    target_multiplexer = Multiplexer()
    multiplexer.transfer(target_multiplexer, proc)

    assert proc in target_multiplexer.procs
    assert proc not in multiplexer.procs

def test_process_empty_procs(multiplexer):
    result = multiplexer.process()
    assert result is None


def test_addtomultiafter_early_finish():
    multi = Multiplexer()

    with patch("builtins.print") as mocked_print:
        addtomultiafter(multi, "test", lambda line: False, ["echo", "early"])
        assert mocked_print.called

    assert len(multi.procs) == 0  # Ensure no processes are left after running


def test_transfer_with_remaining_streams(multiplexer):
    proc = MockProc(stdout=MockStream(b"output\n"))
    multiplexer.addproc("test", proc)

    target_multiplexer = Multiplexer()
    multiplexer.transfer(target_multiplexer, proc)

    assert len(target_multiplexer.streams) == 1
    assert len(multiplexer.streams) == 0



@pytest.fixture
def setup_multiplexer_addproc():
    multi = Multiplexer()
    sp_proc = multi.addproc(
        "long_running_test",
        sp.Popen(
            ["python3", "-u", "-c", """
import time
for i in range(5):
    print(f'Iteration {i}')
    time.sleep(1)
    """],
            stdout=sp.PIPE, stderr=sp.PIPE
        )
    )
    return multi, sp_proc

def test_multiplexer_process_interruption(setup_multiplexer_addproc):
    capture_multi, sp_proc = setup_multiplexer_addproc
    captured_output = []

    def mock_consumelines(self):
        while self.data:
            i = self.data.find(b"\n")
            if i < 0:
                return
            captured_output.append(self.data[:i].decode())
            yield self.data[:i]
            self.data = self.data[i + 1:]

    with patch.object(StreamData, 'consumelines', mock_consumelines):
        try:
            while True:
                capture_multi.process(0.5)

                # Stop processing if all streams have finished
                if not capture_multi.streams:
                    break

        except OutputInteruptedException as ex:
            print("Process was interrupted.")

    # Ensure the subprocess has terminated
    assert sp_proc.poll() is not None, "The subprocess should have been terminated."

    # Verify the captured output contains at least one "Iteration" message
    assert any("Iteration" in line for line in captured_output), "No output was captured."

    assert captured_output == ['Iteration 0', 'Iteration 1', 'Iteration 2', 'Iteration 3', 'Iteration 4']


@pytest.fixture
def setup_multiplexer():
    multi = Multiplexer()
    sp_proc = multi.run(
        "long_running_test",
        ["python3", "-u", "-c", """
import time
for i in range(5):
    print(f'Iteration {i}')
    time.sleep(1)
    """],
        stdout=sp.PIPE, stderr=sp.PIPE
    )
    return multi, sp_proc


def test_multiplexer_run_method(setup_multiplexer):
    multi, sp_proc = setup_multiplexer
    captured_output = []


    def mock_consumelines(self):
        while self.data:
            i = self.data.find(b"\n")
            if i < 0:
                return
            captured_output.append(self.data[:i].decode())
            yield self.data[:i]
            self.data = self.data[i + 1:]

    with patch.object(StreamData, 'consumelines', mock_consumelines):
        try:
            while True:
                multi.process(0.5)

                # Stop processing if all streams have finished
                if not multi.streams:
                    break

        except OutputInteruptedException as ex:
            print("Process was interrupted.")

    # Ensure the subprocess has terminated
    assert sp_proc.poll() is not None, "The subprocess should have been terminated."

    # Verify the captured output contains at least one "Iteration" message
    assert any("Iteration" in line for line in captured_output), "No output was captured."

    # Verify the exact captured output
    assert captured_output == ['Iteration 0', 'Iteration 1', 'Iteration 2', 'Iteration 3', 'Iteration 4']


# def test_multiplexer_transfer_method():
#     # Create two multiplexers
#     multi1 = Multiplexer()
#     multi2 = Multiplexer()
#
#     # Add a long-running subprocess to the first multiplexer
#     sp_proc = multi1.run(
#         "long_running_test",
#         ["python3", "-u", "-c", """
#     import time
#     for i in range(5):
#         print(f'Iteration {i}')
#         time.sleep(1)
#         """],
#         stdout=sp.PIPE, stderr=sp.PIPE
#     )
#
#     # Perform the transfer
#     multi1.transfer(multi2, sp_proc)
#
#     # Process in the second multiplexer
#     captured_output = []
#
#     def mock_consumelines(self):
#         while self.data:
#             i = self.data.find(b"\n")
#             if i < 0:
#                 return
#             captured_output.append(self.data[:i].decode())
#             yield self.data[:i]
#             self.data = self.data[i + 1:]
#
#     with patch.object(StreamData, 'consumelines', mock_consumelines):
#         try:
#             while True:
#                 multi2.process(0.5)
#
#                 # Stop processing if all streams have finished
#                 if not multi2.streams:
#                     break
#
#         except OutputInteruptedException as ex:
#             print("Process was interrupted.")
#
#     # Ensure the subprocess has terminated
#     assert sp_proc.poll() is not None, "The subprocess should have been terminated."
#
#     # Verify the captured output contains at least one "Iteration" message
#     assert any("Iteration" in line for line in captured_output), "No output was captured."
#
#     # Verify the exact captured output
#     assert captured_output == ['Iteration 0', 'Iteration 1', 'Iteration 2', 'Iteration 3', 'Iteration 4']




def test_multiplexer_processall_method(setup_multiplexer):
    multi, sp_proc = setup_multiplexer
    captured_output = []

    def mock_consumelines(self):
        while self.data:
            i = self.data.find(b"\n")
            if i < 0:
                return
            captured_output.append(self.data[:i].decode())
            yield self.data[:i]
            self.data = self.data[i + 1:]

    with patch.object(StreamData, 'consumelines', mock_consumelines):
        try:
            multi.processall()
        except OutputInteruptedException as ex:
            print("Process was interrupted.")

    # Ensure the subprocess has terminated
    assert sp_proc.poll() is not None, "The subprocess should have been terminated."

    # Verify the captured output contains at least one "Iteration" message
    assert any("Iteration" in line for line in captured_output), "No output was captured."

    # Verify the exact captured output
    assert captured_output == ['Iteration 0', 'Iteration 1', 'Iteration 2', 'Iteration 3', 'Iteration 4']


def test_multiplexer_checkreturnvalues_method(setup_multiplexer):
    multi, sp_proc = setup_multiplexer

    def mock_consumelines(self):
        while self.data:
            i = self.data.find(b"\n")
            if i < 0:
                return
            yield self.data[:i]
            self.data = self.data[i + 1:]

    with patch.object(StreamData, 'consumelines', mock_consumelines):
        try:
            multi.processall()
        except OutputInteruptedException as ex:
            print("Process was interrupted.")

    # Ensure the subprocess has terminated
    assert sp_proc.poll() is not None, "The subprocess should have been terminated."

    # Check the return values
    return_values = multi.checkreturnvalues()

    # Verify that the return value of the subprocess is captured
    assert "long_running_test" in return_values
    assert return_values["long_running_test"] == 0, "The subprocess should have finished with status 0."
