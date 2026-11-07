"""Utilities for running and monitoring multiple subprocesses together."""

import os
import selectors
import subprocess as sp


class OutputInteruptedException(Exception):
    """Raised when a watched output stream reaches an interrupt condition."""

    def __init__(self, streams):
        """Store the interrupted stream state so processing can be resumed later."""
        super().__init__("Some streams where interrupted")
        self.streams = streams

    def __str__(self):
        """Return a readable description of the interrupted streams."""
        return "Some streams where interupted: {}".format(
            ", ".join(str(s) for s in self.stream)
        )

    def reapply(self, multi):
        """Reattach the saved line-check callbacks to another multiplexer."""
        for stream, (_, linecheck) in self.streams.items():
            multi.streams[stream].linecheck = linecheck


class StreamData(object):
    """Track buffered data and metadata for one subprocess output stream."""

    def __init__(self, tag, proc, data=None):
        """Initialise the stream state for a specific process output handle."""
        self.tag = tag
        self.proc = proc
        if data is None:
            data = b""
        self.data = data
        self.linecheck = None

    def consumelines(self):
        """Yield complete newline-terminated chunks from the buffered data."""
        while True:
            i = self.data.find(b"\n")
            if i < 0:
                return
            tmp = self.data[:i]

            self.data = self.data[i + 1 :]
            yield tmp


class ProcData(object):
    """Store stream handles associated with a managed subprocess."""

    def __init__(self, tag, streams=None):
        """Initialise the tracked metadata for one subprocess."""
        self.tag = tag
        if streams is None:
            streams = []
        self.streams = streams

    def __iter__(self):
        """Iterate over the stream handles associated with this process."""
        return iter(self.streams)


class Multiplexer(object):
    """Poll and print output from multiple subprocesses at the same time."""

    def __init__(self):
        """Initialise the selector, stream registry, and return-value cache."""
        self.selector = selectors.DefaultSelector()
        self.procs = {}
        self.streams = {}
        self.streamlessprocs = set()
        self.checkdata = set()
        self.returnvalues = {}

    def run(self, tag, *args, **kwargs):
        """Start a subprocess and immediately register it for multiplexing."""
        return self.addproc(tag, sp.Popen(*args, **kwargs))

    def addproc(self, tag, proc):
        """Register a subprocess and any stdout or stderr streams it exposes."""
        self.addbareproc(tag, proc)
        if proc.stdout is not None:
            self.addstream(proc.stdout, proc)
        if proc.stderr is not None:
            self.addstream(proc.stderr, proc)
        return proc

    def addbareproc(self, tag, proc):
        """Register a subprocess before any streams have been attached."""
        if proc not in self.procs:
            self.procs[proc] = ProcData(tag)
        else:
            self.procs[proc].tag = tag
        if not self.procs[proc].streams:
            self.streamlessprocs.add(proc)

    def addstream(self, stream, proc, tag=None, data=None):
        """Register a readable stream so its output can be buffered and printed."""
        if proc in self.streamlessprocs:
            self.streamlessprocs.remove(proc)
        if stream not in self.streams:
            self.streams[stream] = StreamData(tag, proc, data)
            self.procs[proc].streams.append(stream)
            self.selector.register(stream, selectors.EVENT_READ)
            if data is not None:
                self.checkdata.add(stream)
        elif data != self.streams[stream].data:
            raise ValueError(
                (
                    "Error we already know about the stream but "
                    "you provided different state"
                ),
                stream,
                data,
                self.streams[stream].data,
            )
        else:
            self.streams[stream].tag = tag

    def removestream(self, stream):
        """Unregister a stream and return its process, tag, and buffered data."""
        self.selector.unregister(stream)
        data = self.streams[stream]
        self.procs[data.proc].streams.remove(stream)
        del self.streams[stream]
        if not self.procs[data.proc].streams:
            self.streamlessprocs.add(data.proc)
        return data.proc, data.tag, data.data

    def removeproc(self, proc):
        """Remove a process and every stream currently associated with it."""
        for stream in self.procs[proc]:
            self.removestream(stream)
        del self.procs[proc]
        self.streamlessprocs.remove(proc)

    def transfer(self, target, proc):
        """Move a process and its streams from this multiplexer into another."""
        target.addbareproc(self.procs[proc].tag, proc)
        for stream in self.procs[proc].streams:
            target.addstream(stream, *self.removestream(stream))
        # all streams removed so now should be in streamlessprocs
        self.streamlessprocs.remove(proc)
        del self.procs[proc]

    def gettag(self, stream):
        """Build the output prefix shown for a stream in console output."""
        tag = self.procs[self.streams[stream].proc].tag
        if self.streams[stream].tag is not None:
            tag += "-{}".format(self.streams[stream].tag)
        if tag != "":
            tag += ": "
        return tag

    def process(self, timeout=None):
        """Process one round of output and process-exit events."""
        if not self.procs:
            return None
        interuptedstreams = {}
        for stream in self.checkdata:
            stream_data = self.streams[stream]
            for line in stream_data.consumelines():
                if stream_data.linecheck and stream_data.linecheck(line):
                    interuptedstreams[stream] = (line, stream_data.linecheck)
                    stream_data.linecheck = None
                    break
                else:
                    print(self.gettag(stream), line.decode())
        self.checkdata = set()
        if self.streams:
            inputs = self.selector.select(timeout)
            for key, _events in inputs:
                stream = key.fileobj
                stream_data = self.streams[stream]
                new = stream.read1(1000)
                stream_data.data += new
                for line in stream_data.consumelines():
                    if stream_data.linecheck and stream_data.linecheck(line):
                        interuptedstreams[stream] = (line, stream_data.linecheck)
                        stream_data.linecheck = None
                        break
                    else:
                        print(self.gettag(stream), line.decode())
                if not new:  # event but no new data means eof
                    if stream_data.data:  # write out any part line anyway
                        print(self.gettag(stream), stream_data.data.decode())
                    self.removestream(
                        stream
                    )  # adds to streamlessprocs if no streams left
                    key.fileobj.close()
            for proc in list(self.streamlessprocs):
                if proc.poll() is not None:
                    ret = proc.wait()
                    print(
                        "{} has finished with status {}".format(
                            self.procs[proc].tag, ret
                        )
                    )
                    self.returnvalues[self.procs[proc].tag] = ret
                    del self.procs[proc]
                    self.streamlessprocs.remove(proc)
        else:
            _, ret = os.waitpid(-1, 0)
            for proc in list(self.streamlessprocs):
                if proc.poll() is not None:
                    ret = proc.wait()
                    print(
                        "{} has finished with status {}".format(
                            self.procs[proc].tag, ret
                        )
                    )
                    self.returnvalues[self.procs[proc].tag] = ret
                    del self.procs[proc]
                    self.streamlessprocs.remove(proc)
        if interuptedstreams:
            self.checkdata.update(interuptedstreams.keys())
            raise OutputInteruptedException(interuptedstreams)
        return len(self.streams)

    def processall(self):
        """Process events until no tracked subprocesses remain."""
        while self.process() is not None:
            pass

    def checkreturnvalues(self):
        """Return and clear the collected subprocess exit codes."""
        tmp = self.returnvalues
        self.returnvalues = {}
        return tmp


def addtomultiafter(multi, tag, fn, *args, **kwargs):
    """Add a process to a multiplexer once a line predicate reports readiness."""
    tmp = Multiplexer()
    print("Running", tag, flush=True)
    proc = tmp.run("", *args, **kwargs)
    for s in tmp.procs[proc].streams:
        tmp.streams[s].linecheck = fn
    try:
        tmp.processall()
    except OutputInteruptedException:
        print(tag, "is running")
        tmp.transfer(multi, proc)
        multi.procs[proc].tag = tag
    else:
        print("Process {} finished early".format(tag))
    multi.process(1)
    multi.process(0)
