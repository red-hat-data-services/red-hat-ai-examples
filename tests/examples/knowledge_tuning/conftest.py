"""Pytest configuration and fixtures for knowledge-tuning tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def notebook_files(knowledge_tuning_path):
    """Return list of all notebook files in knowledge-tuning."""
    notebooks = list(knowledge_tuning_path.rglob("*.ipynb"))
    return sorted(notebooks)


@pytest.fixture
def pyproject_files(knowledge_tuning_path):
    """Return list of all pyproject.toml files in knowledge-tuning."""
    pyprojects = list(knowledge_tuning_path.rglob("pyproject.toml"))
    return sorted(pyprojects)


def load_notebook(path: Path) -> dict:
    """Load a notebook file and return its content as dict."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def notebook_loader():
    """Return a function to load notebook files."""
    return load_notebook
