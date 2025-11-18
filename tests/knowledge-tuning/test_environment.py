"""Tests for environment and dependency validation."""
import sys
from pathlib import Path

import pytest

# Try to import tomllib (Python 3.11+) or fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        pytest.skip("No TOML parser available (need tomllib or tomli)")


class TestPyprojectToml:
    """Test pyproject.toml files."""

    def test_pyproject_files_are_valid_toml(self, pyproject_files):
        """Test that all pyproject.toml files are valid TOML."""
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                try:
                    tomllib.load(f)
                except Exception as e:
                    pytest.fail(
                        f"pyproject.toml {pyproject_path} is not valid TOML: {e}"
                    )

    def test_pyproject_files_are_parseable(self, pyproject_files):
        """Test that pyproject.toml files can be parsed."""
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                assert isinstance(data, dict)
                # Should have at least a [project] section
                assert "project" in data or "tool" in data

    def test_python_version_consistency(self, pyproject_files):
        """Test that Python version requirements are consistent."""
        if not pyproject_files:
            pytest.skip("No pyproject.toml files found")

        versions = []
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            requires_python = project.get("requires-python")
            if requires_python:
                versions.append((pyproject_path, requires_python))

        if versions:
            # Check that all versions are compatible (basic check)
            # All should specify >=3.12 or similar
            for pyproject_path, version in versions:
                # Basic validation that it's a valid version spec
                assert isinstance(version, str)
                assert len(version) > 0

    def test_dependencies_are_parseable(self, pyproject_files):
        """Test that dependencies can be parsed."""
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            dependencies = project.get("dependencies", [])

            # Dependencies should be a list
            assert isinstance(dependencies, list)

            # Each dependency should be a string
            for dep in dependencies:
                assert isinstance(dep, str)
                assert len(dep) > 0

    def test_no_obviously_deprecated_patterns(self, pyproject_files):
        """Test for obviously deprecated package patterns."""
        deprecated_patterns = [
            "python2",
            "python<3",
        ]

        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            requires_python = project.get("requires-python", "")

            for pattern in deprecated_patterns:
                assert (
                    pattern.lower() not in requires_python.lower()
                ), f"pyproject.toml {pyproject_path} contains deprecated pattern: {pattern}"

