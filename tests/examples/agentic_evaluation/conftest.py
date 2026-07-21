import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def agentic_evaluation_path(repo_root):
    path = repo_root / "examples" / "agentic-evaluation"
    assert path.exists(), "agentic-evaluation directory not found"
    return path


@pytest.fixture
def agentic_tools_module(agentic_evaluation_path):
    spec = importlib.util.spec_from_file_location(
        "agentic_eval_tools",
        agentic_evaluation_path / "tools.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_notebook(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def notebook_loader():
    return load_notebook
