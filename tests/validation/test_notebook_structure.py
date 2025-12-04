"""
Notebook structure validation tests.

Tests that validate basic notebook file structure:
- Valid JSON format
- Valid nbformat schema
- Contains cells
- Has metadata
- Valid cell types
- No execution errors in outputs
"""

import json

import pytest
from nbformat import read, validate
from nbformat.validator import ValidationError


def pytest_generate_tests(metafunc):
    """Generate test parameters from all notebooks."""
    if (
        "notebook_path" in metafunc.fixturenames
        and "relative_path" in metafunc.fixturenames
    ):
        all_notebooks = metafunc.config._notebooks
        metafunc.parametrize("notebook_path,relative_path", all_notebooks)


def test_notebook_is_valid_json(notebook_path, relative_path):
    """Test that notebook is valid JSON."""
    try:
        with open(notebook_path, encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Notebook {relative_path} is not valid JSON: {e}")


def test_notebook_structure(notebook_path, relative_path):
    """Test that notebook has valid nbformat structure."""
    try:
        nb = read(str(notebook_path), as_version=4)
        validate(nb)
    except ValidationError as e:
        pytest.fail(f"Notebook {relative_path} has invalid structure: {e}")
    except Exception as e:
        pytest.fail(f"Error reading notebook {relative_path}: {e}")


def test_notebook_has_cells(notebook_path, relative_path):
    """Test that notebook contains at least one cell."""
    nb = read(str(notebook_path), as_version=4)
    assert len(nb.cells) > 0, f"Notebook {relative_path} has no cells"


def test_notebook_metadata_exists(notebook_path, relative_path):
    """Test that notebook has metadata."""
    nb = read(str(notebook_path), as_version=4)
    assert nb.metadata is not None, f"Notebook {relative_path} has no metadata"


def test_notebook_no_execution_errors(notebook_path, relative_path):
    """Test that notebook cells don't contain execution errors in outputs."""
    nb = read(str(notebook_path), as_version=4)

    errors = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "code" and hasattr(cell, "outputs"):
            for output in cell.outputs:
                if output.get("output_type") == "error":
                    error_info = {
                        "cell_index": i,
                        "ename": output.get("ename", "Unknown"),
                        "evalue": output.get("evalue", "Unknown error"),
                    }
                    errors.append(error_info)

    if errors:
        error_msg = f"Notebook {relative_path} contains {len(errors)} error(s):\n"
        for err in errors:
            error_msg += (
                f"  Cell {err['cell_index']}: {err['ename']}: {err['evalue']}\n"
            )
        pytest.fail(error_msg)


def test_notebook_cells_have_valid_types(notebook_path, relative_path):
    """Test that all cells have valid cell types."""
    nb = read(str(notebook_path), as_version=4)

    valid_cell_types = {"code", "markdown", "raw"}
    invalid_cells = []

    for i, cell in enumerate(nb.cells):
        if cell.cell_type not in valid_cell_types:
            invalid_cells.append((i, cell.cell_type))

    if invalid_cells:
        error_msg = f"Notebook {relative_path} contains cells with invalid types:\n"
        for i, cell_type in invalid_cells:
            error_msg += f"  Cell {i}: {cell_type}\n"
        pytest.fail(error_msg)


def test_all_notebooks_found(all_notebooks):
    """Test that we found at least one notebook to test."""
    assert len(all_notebooks) > 0, "No notebooks found in examples directory"
    print(f"\nFound {len(all_notebooks)} notebooks to validate")
