from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module_from_repo(module_name, relative_path):
    module_path = REPO_ROOT / relative_path
    spec = spec_from_file_location(module_name, module_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
