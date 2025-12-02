"""Pytest configuration and fixtures for knowledge-tuning tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def knowledge_tuning_dir(repo_root: Path) -> Path:
    """Return the examples/knowledge-tuning directory."""
    return repo_root / "examples" / "knowledge-tuning"


@pytest.fixture
def notebook_dirs(knowledge_tuning_dir: Path) -> list[Path]:
    """Return list of directories containing notebooks."""
    dirs = []
    for item in knowledge_tuning_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            # Check if directory contains a .ipynb file
            if any(item.glob("*.ipynb")):
                dirs.append(item)
    return sorted(dirs)


@pytest.fixture
def notebook_files(knowledge_tuning_dir: Path) -> list[Path]:
    """Return list of all notebook files in knowledge-tuning."""
    notebooks = list(knowledge_tuning_dir.rglob("*.ipynb"))
    return sorted(notebooks)


@pytest.fixture
def pyproject_files(knowledge_tuning_dir: Path) -> list[Path]:
    """Return list of all pyproject.toml files in knowledge-tuning."""
    pyprojects = list(knowledge_tuning_dir.rglob("pyproject.toml"))
    return sorted(pyprojects)


def load_notebook(path: Path) -> dict:
    """Load a notebook file and return its content as dict."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def notebook_loader():
    """Return a function to load notebook files."""
    return load_notebook
