"""Pytest fixtures for repo-wide notebook and configuration checks."""

from pathlib import Path
from typing import Iterable

import pytest

IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "test-results",
}


def _is_ignored(path: Path) -> bool:
    """Return True if the path is inside an ignored directory."""
    return (
        any(part in IGNORED_PARTS for part in path.parts)
        or ".ipynb_checkpoints" in path.parts
    )


def _collect_paths(repo_root: Path, pattern: str) -> list[Path]:
    """Collect sorted paths matching the given glob while respecting ignore rules."""
    paths: Iterable[Path] = repo_root.rglob(pattern)
    filtered = [path for path in paths if not _is_ignored(path)]
    return sorted(filtered)


@pytest.fixture(scope="session")
def notebook_files(repo_root: Path) -> list[Path]:
    """Return list of all notebook files in the repository."""
    return _collect_paths(repo_root, "*.ipynb")


@pytest.fixture(scope="session")
def pyproject_files(repo_root: Path) -> list[Path]:
    """Return list of all pyproject.toml files in the repository."""
    return _collect_paths(repo_root, "pyproject.toml")
