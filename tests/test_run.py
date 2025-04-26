import importlib.util
import sys
import os

def test_run_py_importable():
    # This test ensures run.py can be imported without executing the main block
    spec = importlib.util.spec_from_file_location("run", os.path.join(os.path.dirname(__file__), "..", "run.py"))
    run = importlib.util.module_from_spec(spec)
    sys.modules["run"] = run
    spec.loader.exec_module(run)
    assert hasattr(run, "app") or hasattr(run, "create_app")
