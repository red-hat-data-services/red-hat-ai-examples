"""Shared test fixtures and utilities for all tests."""

from pathlib import Path

import pytest

# Try to import tomllib (Python 3.11+) or fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def pytest_configure(config):
    """Configure pytest with custom data."""
    repo_root = Path(__file__).parent.parent
    notebooks = list(repo_root.glob("examples/**/*.ipynb"))
    config._notebooks = [(nb, nb.relative_to(repo_root)) for nb in notebooks]

    pyproject_files = list(repo_root.glob("examples/**/pyproject.toml"))
    root_pyproject = repo_root / "pyproject.toml"
    if root_pyproject.exists():
        pyproject_files.insert(0, root_pyproject)
    config._pyproject_files = pyproject_files


@pytest.fixture(scope="session")
def repo_root():
    """Get repository root path."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def all_notebooks(repo_root):
    """Get all notebooks in examples directory."""
    notebooks = list(repo_root.glob("examples/**/*.ipynb"))
    return [(nb, nb.relative_to(repo_root)) for nb in notebooks]


@pytest.fixture(scope="session")
def all_pyproject_files(repo_root):
    """Get all pyproject.toml files in repository."""
    pyproject_files = list(repo_root.glob("examples/**/pyproject.toml"))
    root_pyproject = repo_root / "pyproject.toml"
    if root_pyproject.exists():
        pyproject_files.insert(0, root_pyproject)
    return pyproject_files


@pytest.fixture(scope="session")
def knowledge_tuning_path(repo_root):
    """Get knowledge-tuning directory path."""
    path = repo_root / "examples" / "knowledge-tuning"
    if not path.exists():
        pytest.skip("knowledge-tuning directory not found")
    return path


# Make tomllib available to all tests
@pytest.fixture(scope="session")
def toml_parser():
    """Get TOML parser (tomllib or tomli)."""
    if tomllib is None:
        pytest.skip("No TOML parser available (need tomllib or tomli)")
    return tomllib
