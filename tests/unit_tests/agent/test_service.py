"""Background reporting recovers from transient lifecycle lock contention."""

from contextlib import contextmanager, nullcontext
import threading
from types import SimpleNamespace

import agent.config as config_module
import agent.service as service_module
from utils.state_io import state_lock
from test_agent import config


def test_reporting_retries_after_lifecycle_config_lock_timeout(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    held, release = threading.Event(), threading.Event()
    sent = []

    def hold_config():
        with state_lock(cfg.path):
            held.set()
            assert release.wait(5)

    holder = threading.Thread(target=hold_config)
    holder.start()
    assert held.wait(2)

    @contextmanager
    def short_lock(path):
        with state_lock(path, timeout=.01):
            yield

    class Stop:
        waits = 0

        def wait(self, _timeout):
            self.waits += 1
            if self.waits == 2:
                release.set()
                holder.join(2)
                assert not holder.is_alive()
            return self.waits > 2

    def request(_method, _path, **kwargs):
        sent.append(kwargs['payload'])
        return {'accepted': True}

    stop = Stop()
    runtime = SimpleNamespace(lock=lambda _tag: nullcontext(), state=lambda _tag: 'running',
                              metadata=lambda _tag, metadata: metadata)
    service = service_module.Service(cfg, runtime=runtime, transport=SimpleNamespace(request=request))
    service.stop = stop
    monkeypatch.setattr(config_module, 'state_lock', short_lock)
    monkeypatch.setattr(service_module, 'time', SimpleNamespace(
        monotonic=lambda: stop.waits * 100, time=lambda: 1800000000))
    try:
        service._report_loop()
    finally:
        release.set()
        holder.join(2)
    assert not holder.is_alive()
    assert len(sent) == 1
    assert sent[0]['sequence'] == cfg.load()['sequence'] == 1
    assert sent[0]['bindings'][0]['runtime_state'] == 'running'
