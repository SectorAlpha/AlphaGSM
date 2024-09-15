import subprocess as sp
import os
import selectors


class OutputInteruptedException(Exception):
    def __init__(self, streams):
        super().__init__("Some streams where interrupted")
        self.streams = streams

    def __str__(self):
        return "Some streams where interupted: {}".format(
            ", ".join(str(s) for s in self.stream)
        )

    def reapply(self, multi):
        for s, (l, f) in self.streams.items():
            multi.streams[s].linecheck = f


class StreamData(object):
    def __init__(self, tag, proc, data=None):
        self.tag = tag
        self.proc = proc
        if data is None:
            data = b""
        self.data = data
        self.linecheck = None

    def consumelines(self):
        while True:
            i = self.data.find(b"\n")
            if i < 0:
                return
            tmp = self.data[:i]

            self.data = self.data[i + 1:]
            yield tmp


class ProcData(object):
    def __init__(self, tag, streams=None):
        self.tag = tag
        if streams is None:
            streams = []
        self.streams = streams

    def __iter__(self):
        return iter(self.streams)


class Multiplexer(object):
    def __init__(self):
        self.selector = selectors.DefaultSelector()
        self.procs = {}
        self.streams = {}
        self.streamlessprocs = set()
        self.checkdata = set()
        self.returnvalues = {}

    def run(self, tag, *args, **kwargs):
        return self.addproc(tag, sp.Popen(*args, **kwargs))

    def addproc(self, tag, proc):
        self.addbareproc(tag, proc)
        if proc.stdout is not None:
            self.addstream(proc.stdout, proc)
        if proc.stderr is not None:
            self.addstream(proc.stderr, proc)
        return proc

    def addbareproc(self, tag, proc):
        if proc not in self.procs:
            self.procs[proc] = ProcData(tag)
        else:
            self.procs[proc].tag = tag
        if not self.procs[proc].streams:
            self.streamlessprocs.add(proc)

    def addstream(self, stream, proc, tag=None, data=None):
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
                ), stream, data, self.streams[stream].data
            )
        else:
            self.streams[stream].tag = tag

    def removestream(self, stream):
        self.selector.unregister(stream)
        data = self.streams[stream]
        self.procs[data.proc].streams.remove(stream)
        del self.streams[stream]
        if not self.procs[data.proc].streams:
            self.streamlessprocs.add(data.proc)
        return data.proc, data.tag, data.data

    def removeproc(self, proc):
        for stream in self.procs[proc]:
            self.removestream(stream)
        del self.procs[proc]
        self.streamlessprocs.remove(proc)

    def transfer(self, target, proc):
        target.addbareproc(self.procs[proc].tag, proc)
        for stream in self.procs[proc].streams:
            target.addstream(stream, *self.removestream(stream))
        # all streams removed so now should be in streamlessprocs
        self.streamlessprocs.remove(proc)
        del self.procs[proc]

    def gettag(self, stream):
        tag = self.procs[self.streams[stream].proc].tag
        if self.streams[stream].tag is not None:
            tag += "-{}".format(self.streams[stream].tag)
        if tag != "":
            tag += ": "
        return tag

    def process(self, timeout=None):
        if not self.procs:
            return None
        interuptedstreams = {}
        for stream in self.checkdata:
            stream_data = self.streams[stream]
            for l in stream_data.consumelines():
                if stream_data.linecheck and stream_data.linecheck(l):
                    interuptedstreams[stream] = (l, stream_data.linecheck)
                    stream_data.linecheck = None
                    break
                else:
                    print(self.gettag(stream), l.decode())
        self.checkdata = set()
        if self.streams:
            inputs = self.selector.select(timeout)
            for key, events in inputs:
                stream = key.fileobj
                stream_data = self.streams[stream]
                new = stream.read1(1000)
                stream_data.data += new
                for l in stream_data.consumelines():
                    if stream_data.linecheck and stream_data.linecheck(l):
                        interuptedstreams[stream] = (l, stream_data.linecheck)
                        stream_data.linecheck = None
                        break
                    else:
                        print(self.gettag(stream), l.decode())
                if not new:  # event but no new data means eof
                    if stream_data.data:  # write out any part line anyway
                        print(
                            self.gettag(stream),
                            stream_data.data.decode()
                        )
                    self.removestream(
                        stream
                    )  # adds to streamlessprocs if no streams left
                    key.fileobj.close()
            for proc in list(self.streamlessprocs):
                if proc.poll() is not None:
                    ret = proc.wait()
                    print("{} has finished with status {}".format(
                        self.procs[proc].tag, ret
                    ))
                    self.returnvalues[self.procs[proc].tag] = ret
                    del self.procs[proc]
                    self.streamlessprocs.remove(proc)
        else:
            pid, ret = os.waitpid(-1, 0)
            for proc in list(self.streamlessprocs):
                if proc.poll() is not None:
                    ret = proc.wait()
                    print("{} has finished with status {}".format(
                        self.procs[proc].tag, ret
                    ))
                    self.returnvalues[self.procs[proc].tag] = ret
                    del self.procs[proc]
                    self.streamlessprocs.remove(proc)
        if interuptedstreams:
            self.checkdata.update(interuptedstreams.keys())
            raise OutputInteruptedException(interuptedstreams)
        return len(self.streams)

    def processall(self):
        while self.process() is not None:
            pass

    def checkreturnvalues(self):
        tmp = self.returnvalues
        self.returnvalues = {}
        return tmp


def addtomultiafter(multi, tag, fn, *args, **kwargs):
    tmp = Multiplexer()
    print("Running", tag, flush=True)
    proc = tmp.run("", *args, **kwargs)
    for s in tmp.procs[proc].streams:
        tmp.streams[s].linecheck = fn
    try:
        tmp.processall()
    except OutputInteruptedException as ex:
        print(tag, "is running")
        tmp.transfer(multi, proc)
        multi.procs[proc].tag = tag
    else:
        print("Process {} finished early".format(tag))
    multi.process(1)
    multi.process(0)
