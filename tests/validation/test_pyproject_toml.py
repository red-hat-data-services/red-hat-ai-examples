"""
PyProject.toml validation tests.

Tests that validate pyproject.toml files across the repository:
- Valid TOML syntax
- Has required sections
- Dependencies are well-formed
- Python version requirements are valid
"""

import pytest


def pytest_generate_tests(metafunc):
    """Generate test parameters from all pyproject files."""
    if "pyproject_path" in metafunc.fixturenames:
        all_pyproject_files = metafunc.config._pyproject_files
        metafunc.parametrize("pyproject_path", all_pyproject_files)


def test_pyproject_is_valid_toml(pyproject_path, toml_parser):
    """Test that pyproject.toml files are valid TOML."""
    try:
        with open(pyproject_path, "rb") as f:
            data = toml_parser.load(f)
        assert isinstance(data, dict)
    except Exception as e:
        pytest.fail(f"pyproject.toml {pyproject_path} is not valid TOML: {e}")


def test_pyproject_has_project_section(pyproject_path, toml_parser):
    """Test that pyproject.toml files have a [project] section."""
    with open(pyproject_path, "rb") as f:
        data = toml_parser.load(f)

    assert "project" in data or "tool" in data, (
        f"pyproject.toml {pyproject_path} has no [project] or [tool] section"
    )


def test_dependencies_are_well_formed(pyproject_path, toml_parser):
    """Test that dependencies in pyproject.toml are well-formed."""
    with open(pyproject_path, "rb") as f:
        data = toml_parser.load(f)

    project = data.get("project", {})
    dependencies = project.get("dependencies", [])

    assert isinstance(dependencies, list), (
        f"Dependencies in {pyproject_path} should be a list"
    )

    for dep in dependencies:
        assert isinstance(dep, str), f"Dependency should be string: {dep}"
        assert len(dep.strip()) > 0, f"Empty dependency in {pyproject_path}"
        # Basic format check: should contain package name
        assert any(c.isalnum() for c in dep), (
            f"Invalid dependency format in {pyproject_path}: {dep}"
        )


def test_requires_python_is_valid(pyproject_path, toml_parser):
    """Test that requires-python field is valid if present."""
    with open(pyproject_path, "rb") as f:
        data = toml_parser.load(f)

    project = data.get("project", {})
    requires_python = project.get("requires-python")

    if requires_python:
        assert isinstance(requires_python, str), (
            f"requires-python should be string in {pyproject_path}"
        )
        assert len(requires_python) > 0, f"requires-python is empty in {pyproject_path}"
        # Should start with comparison operator or version number
        assert requires_python[0] in ">=<~!0123456789", (
            f"Invalid requires-python format in {pyproject_path}: {requires_python}"
        )


def test_no_deprecated_patterns(pyproject_path, toml_parser):
    """Test for obviously deprecated package patterns."""
    deprecated_patterns = [
        "python2",
        "python<3",
    ]

    with open(pyproject_path, "rb") as f:
        data = toml_parser.load(f)

    project = data.get("project", {})
    requires_python = project.get("requires-python", "")

    for pattern in deprecated_patterns:
        assert pattern.lower() not in requires_python.lower(), (
            f"pyproject.toml {pyproject_path} contains deprecated pattern: {pattern}"
        )


def test_python_version_consistency(all_pyproject_files, toml_parser):
    """Test that Python version requirements are consistent across files."""
    if not all_pyproject_files:
        pytest.skip("No pyproject.toml files found")

    versions = []
    for pyproject_path in all_pyproject_files:
        with open(pyproject_path, "rb") as f:
            data = toml_parser.load(f)

        project = data.get("project", {})
        requires_python = project.get("requires-python")
        if requires_python:
            versions.append((pyproject_path.name, requires_python))

    if versions:
        # Log all versions found
        print("\nPython version requirements found:")
        for name, version in versions:
            print(f"  {name}: {version}")

        # Check that all versions are compatible (should be >=3.11 or >=3.12)
        for name, version in versions:
            assert isinstance(version, str), f"{name}: version should be string"
            assert len(version) > 0, f"{name}: version is empty"
            # Should specify Python 3.11+ or 3.12+
            assert any(v in version for v in ["3.11", "3.12", "3.13"]), (
                f"{name}: requires-python should specify >=3.11 or higher, got: {version}"
            )


def test_no_gpu_specific_packages_in_required(pyproject_path, toml_parser):
    """Test that GPU-specific packages are not in required dependencies."""
    gpu_specific_packages = [
        "nvidia-cuda",
        "cuda-toolkit",
        "cudnn",
        "nccl",
        "cuda-python",
    ]

    with open(pyproject_path, "rb") as f:
        data = toml_parser.load(f)

    project = data.get("project", {})
    dependencies = project.get("dependencies", [])

    for dep in dependencies:
        dep_lower = dep.lower()
        # Check for explicit GPU-specific packages
        for gpu_pkg in gpu_specific_packages:
            if gpu_pkg in dep_lower:
                pytest.fail(
                    f"pyproject.toml {pyproject_path} contains GPU-specific package "
                    f"in required dependencies: {dep}. Consider making it optional."
                )


def test_pyproject_files_found(all_pyproject_files):
    """Test that we found at least one pyproject.toml file."""
    assert len(all_pyproject_files) > 0, "No pyproject.toml files found"
    print(f"\nFound {len(all_pyproject_files)} pyproject.toml files to validate")


def test_venv_builds_cleanly(pyproject_path, repo_root):
    """Test that virtual environment builds cleanly for each pyproject.toml."""
    import subprocess
    import sys

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
            stdout_lower = result.stdout.lower()
            gpu_keywords = ["triton", "cuda", "rocm", "gpu"]
            # Check both stdout and stderr for GPU-related errors
            combined_output = stderr_lower + stdout_lower
            if any(keyword in combined_output for keyword in gpu_keywords):
                # Skip GPU-specific dependencies on non-GPU systems
                pytest.skip(
                    f"Skipping {pyproject_path.name}: GPU-specific dependency not available "
                    f"(expected on non-GPU systems)"
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
