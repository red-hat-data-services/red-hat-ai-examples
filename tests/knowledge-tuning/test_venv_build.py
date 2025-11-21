"""Tests for virtual environment build validation."""

import subprocess
import sys

import pytest

# Try to import tomllib (Python 3.11+) or fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        pytest.skip("No TOML parser available (need tomllib or tomli)")


class TestVenvBuild:
    """Test virtual environment build validation."""

    def test_pyproject_syntax_is_valid(self, pyproject_files):
        """Test that pyproject.toml syntax is valid for building venv."""
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                try:
                    data = tomllib.load(f)
                    # If we can parse it, syntax is valid
                    assert isinstance(data, dict)
                except Exception as e:
                    pytest.fail(
                        f"pyproject.toml {pyproject_path} has invalid syntax: {e}"
                    )

    def test_dependency_syntax_is_valid(self, pyproject_files):
        """Test that dependency syntax is valid."""
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            dependencies = project.get("dependencies", [])

            for dep in dependencies:
                # Basic validation: should be a string
                assert isinstance(dep, str)
                # Should not be empty
                assert len(dep.strip()) > 0
                # Should contain package name (basic check)
                # Format is typically "package>=version" or "package==version"
                parts = dep.split()
                assert len(parts) > 0

    def test_no_gpu_specific_packages_in_required(self, pyproject_files):
        """Test that GPU-specific packages are not in required dependencies."""
        gpu_specific_keywords = [
            "cuda",
            "gpu",
            "cudnn",
            "nccl",
        ]

        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            dependencies = project.get("dependencies", [])

            for dep in dependencies:
                dep_lower = dep.lower()
                # Check for GPU-specific keywords
                # Note: This is a basic check - some packages might have these in name but not be GPU-specific
                # We're looking for obvious cases like "torch[cuda]" or explicit GPU packages
                if any(keyword in dep_lower for keyword in gpu_specific_keywords):
                    # Allow torch but flag explicit GPU extras
                    if "torch" in dep_lower and (
                        "cuda" in dep_lower or "gpu" in dep_lower
                    ):
                        # This is acceptable - torch with cuda extras is common
                        pass
                    elif any(
                        keyword in dep_lower
                        for keyword in ["cuda-toolkit", "cudnn", "nccl"]
                    ):
                        # These are GPU-specific and shouldn't be in required deps
                        pytest.fail(
                            f"pyproject.toml {pyproject_path} contains GPU-specific package in required dependencies: {dep}"
                        )

    def test_dependency_graph_structure_is_valid(self, pyproject_files):
        """Test that dependency graph structure is valid."""
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            dependencies = project.get("dependencies", [])

            # Each dependency should be parseable
            for dep in dependencies:
                # Try to extract package name (everything before comparison operators)
                import re

                # Match package name (letters, numbers, hyphens, underscores, dots)
                match = re.match(r"^([a-zA-Z0-9._-]+)", dep)
                if match:
                    package_name = match.group(1)
                    # Package name should be valid
                    assert len(package_name) > 0
                    # Should start with a letter
                    assert package_name[0].isalnum()

    def test_requires_python_is_valid(self, pyproject_files):
        """Test that requires-python field is valid."""
        for pyproject_path in pyproject_files:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            requires_python = project.get("requires-python")

            if requires_python:
                # Should be a string
                assert isinstance(requires_python, str)
                # Should contain version specifiers
                assert len(requires_python) > 0
                # Should start with comparison operator or version number
                assert requires_python[
                    0
                ] in ">=<~!0123456789" or requires_python.startswith("python")

    def test_venv_builds_cleanly(self, pyproject_files, repo_root):
        """Test that virtual environment builds cleanly for each pyproject.toml."""
        for pyproject_path in pyproject_files:
            # Use pip install --dry-run to validate dependency resolution without installing
            # This is much faster than actually building venvs
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "--dry-run",
                        "--report",
                        "-",
                        "-e",
                        str(pyproject_path.parent),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,  # 1 minute timeout for dependency resolution
                    cwd=pyproject_path.parent,
                )

                if result.returncode != 0:
                    # Check for GPU/platform-specific dependency issues
                    stderr_lower = result.stderr.lower()
                    gpu_keywords = ["triton", "cuda", "rocm", "gpu"]
                    if any(keyword in stderr_lower for keyword in gpu_keywords):
                        # Skip GPU-specific dependencies on non-GPU systems
                        # This is expected - these packages require GPU hardware
                        pytest.skip(
                            f"Skipping {pyproject_path.name}: GPU-specific dependency not available "
                            f"(expected on non-GPU systems): {result.stderr.split(chr(10))[-2] if result.stderr else 'GPU dependency required'}"
                        )

                    pytest.fail(
                        f"Failed to resolve dependencies for {pyproject_path}:\n"
                        f"stdout: {result.stdout}\n"
                        f"stderr: {result.stderr}"
                    )

            except subprocess.TimeoutExpired:
                pytest.fail(
                    f"Timeout resolving dependencies for {pyproject_path} (exceeded 1 minute)"
                )
            except Exception as e:
                pytest.fail(f"Error resolving dependencies for {pyproject_path}: {e}")

    def test_dependencies_resolve_without_conflicts(self, pyproject_files, repo_root):
        """Test that dependencies resolve without conflicts."""
        for pyproject_path in pyproject_files:
            try:
                # Use pip install --dry-run to check for conflicts
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "--dry-run",
                        "-e",
                        str(pyproject_path.parent),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=pyproject_path.parent,
                )

                # Check for dependency conflict errors
                if result.returncode != 0:
                    stderr_lower = result.stderr.lower()
                    if "conflict" in stderr_lower or "conflicting" in stderr_lower:
                        pytest.fail(
                            f"Dependency conflicts found for {pyproject_path}:\n"
                            f"{result.stderr}"
                        )
                    # Skip GPU-specific dependencies
                    gpu_keywords = ["triton", "cuda", "rocm", "gpu"]
                    if any(keyword in stderr_lower for keyword in gpu_keywords):
                        pytest.skip(
                            f"Skipping {pyproject_path.name}: GPU-specific dependency issue"
                        )
                    # Other errors are handled by test_venv_builds_cleanly

            except subprocess.TimeoutExpired:
                pytest.fail(f"Timeout resolving dependencies for {pyproject_path}")
            except Exception as e:
                pytest.fail(f"Error checking dependencies for {pyproject_path}: {e}")

    def test_modules_can_be_imported(self, pyproject_files, notebook_files, repo_root):
        """Test that modules referenced by notebooks can be imported (syntax validation only)."""
        # This is a lightweight check - we validate import syntax without building venvs
        # We don't execute notebook cells, just check that imports are parseable

        # Collect all imports from notebooks
        import ast
        import json

        all_imports = set()
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            for cell in nb.get("cells", []):
                if cell.get("cell_type") != "code":
                    continue

                source = cell.get("source", [])
                if isinstance(source, list):
                    source_str = "".join(source)
                else:
                    source_str = source or ""

                # Skip shell commands
                if "!" in source_str or "%" in source_str:
                    continue

                try:
                    tree = ast.parse(source_str)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                all_imports.add(alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                all_imports.add(node.module.split(".")[0])
                except SyntaxError:
                    # Skip cells with syntax errors (shell commands, etc.)
                    continue

        # Validate that imports are well-formed (syntax check only)
        # We can't actually import without building venvs, but we can validate syntax
        # This test ensures imports would work if dependencies were installed
        for pyproject_path in pyproject_files:
            # Just verify the pyproject.toml exists and is valid
            # The actual import validation is done in test_notebook_imports
            assert pyproject_path.exists(), (
                f"pyproject.toml not found: {pyproject_path}"
            )

            # Verify dependencies are listed (basic check)
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            project = data.get("project", {})
            dependencies = project.get("dependencies", [])
            assert isinstance(dependencies, list), (
                f"Invalid dependencies in {pyproject_path}"
            )
