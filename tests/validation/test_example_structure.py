"""
Example file structure validation tests.

Tests that validate required files and directory structure:
- Required files present (README, metadata, dependencies)
- Naming conventions followed
- Directory structure matches metadata
"""

import json
import re
from pathlib import Path

import pytest
import yaml


def pytest_generate_tests(metafunc):
    """Generate test parameters from all example directories."""
    if "example_path" in metafunc.fixturenames:
        repo_root = Path(__file__).parent.parent.parent
        examples_dir = repo_root / "examples"

        example_dirs = [
            d
            for d in examples_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        metafunc.parametrize("example_path", example_dirs)


@pytest.mark.validation_warning
def test_required_files_present(example_path):
    """Test that required files are present."""
    # README is always required
    readme = example_path / "README.md"
    assert readme.exists(), (
        f"Missing README.md in {example_path.name}. "
        f"See docs/EXAMPLE_STYLE_GUIDE.md for README structure."
    )


def test_directory_naming_convention(example_path):
    """Test that directory names follow naming conventions."""
    name = example_path.name

    # Should be lowercase with hyphens (or numbered module format)
    # Allow: knowledge-tuning, 00_Setup
    assert name.islower() or name[0].isdigit(), (
        f"Directory name '{name}' should be lowercase. "
        f"See docs/EXAMPLE_STYLE_GUIDE.md for naming conventions."
    )

    # No spaces
    assert " " not in name, (
        f"Directory name '{name}' contains spaces. Use hyphens instead."
    )

    # Only hyphens, underscores, alphanumeric
    assert re.match(r"^[a-z0-9_-]+$", name, re.IGNORECASE), (
        f"Directory name '{name}' contains invalid characters. "
        f"Use only lowercase letters, numbers, hyphens, and underscores."
    )


@pytest.mark.validation_warning
def test_readme_has_title(example_path):
    """Test that README has a title (H1 heading)."""
    readme = example_path / "README.md"
    if not readme.exists():
        pytest.skip(f"No README in {example_path.name}")

    content = readme.read_text()
    lines = content.split("\n")

    # Find first H1
    has_h1 = any(line.strip().startswith("# ") for line in lines)
    assert has_h1, (
        f"README in {example_path.name} missing H1 title. "
        f"First line should start with '# Title'"
    )


@pytest.mark.validation_warning
def test_env_example_if_env_vars_used(example_path):
    """Test that .env.example exists if notebooks use env vars."""
    # Find all notebooks
    notebooks = list(example_path.rglob("*.ipynb"))
    if not notebooks:
        pytest.skip(f"No notebooks in {example_path.name}")

    # Check if any notebook uses os.environ or load_dotenv
    uses_env_vars = False
    for nb_path in notebooks:
        try:
            with open(nb_path) as f:
                nb = json.load(f)

            for cell in nb.get("cells", []):
                if cell.get("cell_type") == "code":
                    source = "".join(cell.get("source", []))
                    if "os.environ" in source or "load_dotenv" in source:
                        uses_env_vars = True
                        break
        except Exception:
            continue

        if uses_env_vars:
            break

    if uses_env_vars:
        env_example = (example_path / ".env.example").exists() or (
            example_path / "env.example"
        ).exists()
        assert env_example, (
            f"Notebooks in {example_path.name} use env vars but no .env.example found. "
            f"Create .env.example to document required environment variables."
        )


def test_no_spaces_in_filenames(example_path):
    """Test that no files have spaces in their names."""
    files_with_spaces = []
    for file_path in example_path.rglob("*"):
        if " " in file_path.name:
            files_with_spaces.append(file_path.relative_to(example_path))

    assert not files_with_spaces, (
        f"Files with spaces in names found in {example_path.name}: "
        f"{files_with_spaces}. Use underscores or hyphens instead."
    )


def test_notebooks_use_descriptive_names(example_path):
    """Test that notebooks have descriptive names, not generic ones."""
    generic_names = {
        "test.ipynb",
        "example.ipynb",
        "notebook.ipynb",
        "temp.ipynb",
        "untitled.ipynb",
        "notebook1.ipynb",
        "notebook2.ipynb",
    }

    notebooks = list(example_path.rglob("*.ipynb"))
    for nb_path in notebooks:
        assert nb_path.name.lower() not in generic_names, (
            f"Notebook has generic name '{nb_path.name}' in {example_path.name}. "
            f"Use descriptive name indicating notebook's purpose."
        )


def test_python_scripts_use_snake_case(example_path):
    """Test that Python scripts use snake_case naming."""
    python_files = list(example_path.rglob("*.py"))

    # Exclude __init__.py, setup.py, and files in hidden dirs
    python_files = [
        f
        for f in python_files
        if not f.name.startswith("__")
        and "setup.py" not in f.name
        and not any(part.startswith(".") for part in f.parts)
    ]

    for py_file in python_files:
        # Check if name follows snake_case (lowercase with underscores)
        # Allow numbers but not at the start
        name_without_ext = py_file.stem
        is_snake_case = re.match(r"^[a-z][a-z0-9_]*$", name_without_ext)

        assert is_snake_case, (
            f"Python file '{py_file.name}' in {example_path.name} "
            f"should use snake_case naming. "
            f"Example: knowledge_generation_pipeline.py"
        )


def test_module_readme_naming_for_multi_module(example_path):
    """Test that multi-module examples have properly named module READMEs."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    structure_type = data.get("metadata", {}).get("structure", {}).get("type")

    if structure_type == "multi-module":
        modules = data.get("metadata", {}).get("structure", {}).get("modules", [])

        for module in modules:
            module_dir = example_path / module

            if module_dir.is_dir():
                # Check for module-specific README
                # Format should be: {ModuleName}_README.md or README.md
                readmes = list(module_dir.glob("*README.md"))

                assert len(readmes) > 0, (
                    f"Module directory '{module}' in {example_path.name} "
                    f"missing README file. Each module should have a README."
                )


def test_no_uppercase_only_filenames(example_path):
    """Test that files don't use all-uppercase names (except allowed files)."""
    allowed_uppercase = {"README.md", "LICENSE", "CONTRIBUTING.md", "TESTING.md"}
    # Directories to skip (build artifacts, package metadata)
    skip_dirs = {".egg-info", "dist", "build", "__pycache__", ".pytest_cache"}

    for file_path in example_path.rglob("*"):
        if file_path.is_file():
            # Skip files in build/package metadata directories
            if any(
                part.endswith(tuple(skip_dirs)) or part in skip_dirs
                for part in file_path.parts
            ):
                continue

            name = file_path.name
            # Check if all letters are uppercase (excluding extensions)
            stem = file_path.stem
            if stem.isupper() and name not in allowed_uppercase:
                pytest.fail(
                    f"File '{name}' in {example_path.name} uses all-uppercase name. "
                    f"Use lowercase or mixed-case instead."
                )


def test_env_example_format(example_path):
    """Test that .env.example files follow proper format."""
    env_files = list(example_path.rglob(".env.example")) + list(
        example_path.rglob("env.example")
    )

    for env_file in env_files:
        content = env_file.read_text()
        lines = content.split("\n")

        # Check that there are some comments
        comment_lines = [line for line in lines if line.strip().startswith("#")]
        assert len(comment_lines) > 0, (
            f"Environment file {env_file.relative_to(example_path)} "
            f"missing comments. Add comments to explain each variable."
        )


def test_no_committed_env_files(example_path):
    """Test that actual .env files are not committed."""
    env_files = list(example_path.rglob(".env"))

    # Filter out .env.example files
    actual_env_files = [f for f in env_files if f.name == ".env"]

    assert not actual_env_files, (
        f"Actual .env files found in {example_path.name}: {actual_env_files}. "
        f"Never commit .env files with real credentials. "
        f"Use .env.example instead."
    )


def test_metadata_file_is_example_yaml(example_path):
    """Test that metadata file is named example.yaml, not metadata.yaml."""
    metadata_file = example_path / "metadata.yaml"
    if metadata_file.exists():
        pytest.fail(
            f"Found metadata.yaml in {example_path.name}. "
            f"Rename to example.yaml for consistency."
        )


def test_notebooks_not_in_root_for_multi_module(example_path):
    """Test that multi-module examples don't have notebooks in root."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    structure_type = data.get("metadata", {}).get("structure", {}).get("type")

    if structure_type == "multi-module":
        # Check for notebooks in root directory (not in subdirectories)
        root_notebooks = [f for f in example_path.glob("*.ipynb")]

        # Allow notebooks in root if they're explicitly listed in entry_point
        entry_point = data.get("metadata", {}).get("structure", {}).get("entry_point")

        for nb in root_notebooks:
            if entry_point != nb.name:
                pytest.fail(
                    f"Multi-module example {example_path.name} has notebook "
                    f"'{nb.name}' in root. Notebooks should be in module directories."
                )


def test_dependencies_have_versions(example_path):
    """Test that dependencies specify version constraints.

    Checks both root pyproject.toml and module pyproject.toml files
    for multi-module examples.
    """
    # Find all pyproject.toml files (root and in subdirectories)
    pyproject_files = list(example_path.rglob("pyproject.toml"))

    if not pyproject_files:
        pytest.skip(f"No pyproject.toml in {example_path.name}")

    # Try to import tomllib (Python 3.11+) or fall back to tomli
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            pytest.skip("No TOML parser available (need tomllib or tomli)")

    for pyproject_file in pyproject_files:
        with open(pyproject_file, "rb") as f:
            try:
                pyproject = tomllib.load(f)
            except Exception:
                # If TOML is invalid, other tests will catch it
                continue

        dependencies = pyproject.get("project", {}).get("dependencies", [])

        for dep in dependencies:
            # Check if dependency has version specifier
            # Allow: package>=1.0, package==1.0, package~=1.0
            # Warning if: package (no version)
            has_version = any(op in dep for op in [">=", "<=", "==", "~=", ">", "<"])

            if not has_version and dep.strip():
                # Only warn for now, as this is a recommendation
                print(
                    f"Warning: Dependency '{dep}' in "
                    f"{pyproject_file.relative_to(example_path)} "
                    f"has no version constraint. Consider adding version specifiers."
                )
