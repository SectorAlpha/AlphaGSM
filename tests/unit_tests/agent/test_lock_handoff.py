"""A bounded helper cannot release the parent's lock or select a different inode."""
import subprocess
import sys
import pytest
from utils.state_io import state_lock, held_descriptor, inherited_state_lock


def test_child_reuses_lock_without_unlocking_parent(tmp_path):
    path=tmp_path/'server.json'
    with state_lock(path):
        fd=held_descriptor(path)
        child="""import sys
from utils.state_io import inherited_state_lock, state_lock
with inherited_state_lock(sys.argv[1], int(sys.argv[2])):
    with state_lock(sys.argv[1], timeout=.1): pass
"""
        subprocess.run([sys.executable,'-c',child,str(path),str(fd)],pass_fds=(fd,),check=True,timeout=5)
        contender="""import sys
from utils.state_io import state_lock
try:
    with state_lock(sys.argv[1],timeout=.1): pass
except TimeoutError: sys.exit(0)
sys.exit(1)
"""
        subprocess.run([sys.executable,'-c',contender,str(path)],check=True,timeout=5)
        other=tmp_path/'other.json'
        with state_lock(other):
            with pytest.raises(ValueError):
                with inherited_state_lock(other,fd): pass
    assert held_descriptor(path) is None
    with state_lock(path,timeout=.1): pass
