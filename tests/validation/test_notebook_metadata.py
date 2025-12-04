"""
Notebook metadata validation tests.

Tests that validate notebook metadata consistency and quality:
- Kernelspec consistency across notebooks
- No environment-specific metadata
- Standardized metadata schema
- Required documentation sections
- Logical cell ordering
"""

import json

import pytest


def pytest_generate_tests(metafunc):
    """Generate test parameters from all notebooks."""
    if (
        "notebook_path" in metafunc.fixturenames
        and "relative_path" in metafunc.fixturenames
    ):
        all_notebooks = metafunc.config._notebooks
        metafunc.parametrize("notebook_path,relative_path", all_notebooks)


def test_kernelspec_consistency(all_notebooks):
    """Test that all notebooks have consistent kernelspec.name."""
    if not all_notebooks:
        pytest.skip("No notebooks found")

    kernelspecs = []
    for notebook_path, relative_path in all_notebooks:
        with open(notebook_path, encoding="utf-8") as f:
            nb = json.load(f)

        kernelspec = nb.get("metadata", {}).get("kernelspec", {})
        kernelspec_name = kernelspec.get("name")
        if kernelspec_name:
            kernelspecs.append((relative_path, kernelspec_name))

    if not kernelspecs:
        pytest.skip("No notebooks with kernelspec found")

    # Get the first kernelspec name as the reference
    first_name = kernelspecs[0][1]
    inconsistent = []
    for relative_path, name in kernelspecs:
        if name != first_name:
            inconsistent.append((relative_path, name, first_name))

    if inconsistent:
        error_msg = "Notebooks have inconsistent kernelspec.name:\n"
        for path, name, expected in inconsistent:
            error_msg += f"  {path}: '{name}' (expected '{expected}')\n"
        pytest.fail(error_msg)


def test_no_environment_specific_metadata(notebook_path, relative_path):
    """Test that notebooks don't contain environment-specific metadata."""
    env_specific_keys = [
        "execution",
        "executor",
        "interpreter",
        "vscode",
        "colab",
        "kaggle",
        "widgets",
    ]

    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    metadata = nb.get("metadata", {})
    found_keys = []

    for key in env_specific_keys:
        if key in metadata:
            found_keys.append(key)

    if found_keys:
        pytest.fail(
            f"Notebook {relative_path} contains environment-specific metadata keys: {found_keys}"
        )


def test_standardized_metadata_schema(all_notebooks):
    """Test that all notebooks follow a standardized metadata schema."""
    if not all_notebooks:
        pytest.skip("No notebooks found")

    # Load first notebook to establish schema
    first_path, first_relative = all_notebooks[0]
    with open(first_path, encoding="utf-8") as f:
        first_nb = json.load(f)
    first_metadata_keys = set(first_nb.get("metadata", {}).keys())

    # Core metadata keys that should be consistent
    core_keys = {"kernelspec", "language_info"}
    first_core = first_metadata_keys & core_keys

    inconsistent = []
    for notebook_path, relative_path in all_notebooks[1:]:
        with open(notebook_path, encoding="utf-8") as f:
            nb = json.load(f)

        metadata_keys = set(nb.get("metadata", {}).keys())
        current_core = metadata_keys & core_keys

        if first_core != current_core:
            inconsistent.append((relative_path, current_core, first_core))

    if inconsistent:
        error_msg = "Notebooks have inconsistent core metadata keys:\n"
        for path, current, expected in inconsistent:
            error_msg += f"  {path}: {current} (expected {expected})\n"
        pytest.fail(error_msg)


def test_required_sections_exist(notebook_path, relative_path):
    """Test that notebooks contain required documentation sections."""
    required_keywords = [
        "import",
        "setup",
        "install",
    ]

    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    # Collect all markdown cell content
    markdown_content = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = cell.get("source", [])
            if isinstance(source, list):
                markdown_content.extend(source)
            elif isinstance(source, str):
                markdown_content.append(source)

    content_lower = " ".join(markdown_content).lower()

    # Check for at least one required keyword
    found_keywords = [
        keyword for keyword in required_keywords if keyword in content_lower
    ]

    # At minimum, should have import or install/setup
    if len(found_keywords) == 0:
        pytest.fail(
            f"Notebook {relative_path} missing required sections (imports, setup, or install)"
        )


def test_cell_type_ordering(notebook_path, relative_path):
    """Test that notebooks have logical ordering of cells."""
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb.get("cells", [])
    if len(cells) < 2:
        pytest.skip(f"Notebook {relative_path} has fewer than 2 cells")

    # First cell should typically be markdown (title/overview)
    first_cell_type = cells[0].get("cell_type")
    valid_first_types = ["markdown", "code"]

    if first_cell_type not in valid_first_types:
        pytest.fail(
            f"Notebook {relative_path} first cell has unexpected type: {first_cell_type}"
        )
