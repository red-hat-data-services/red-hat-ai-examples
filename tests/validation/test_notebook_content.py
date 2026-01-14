"""
Notebook content validation tests.

Tests that validate notebook cleanliness and content quality:
- No execution counts (should be cleared)
- No stored outputs (should be cleared)
- No empty code cells
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


def test_no_execution_counts(notebook_path, relative_path):
    """Test that notebooks have no execution counts (should be cleared)."""
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    cells_with_counts = []
    for i, cell in enumerate(nb.get("cells", [])):
        execution_count = cell.get("execution_count")
        if execution_count is not None:
            cells_with_counts.append((i, execution_count))

    if cells_with_counts:
        error_msg = (
            f"Notebook {relative_path} has execution counts (should be cleared):\n"
        )
        for i, count in cells_with_counts:
            error_msg += f"  Cell {i}: execution_count={count}\n"
        pytest.fail(error_msg)


def test_no_stored_outputs(notebook_path, relative_path):
    """Test that notebooks have no stored outputs (should be cleared).

    Cells with 'keep_output' tag in metadata are ignored.
    """
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    cells_with_outputs = []
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            # Check if cell has keep_output tag
            metadata = cell.get("metadata", {})
            tags = metadata.get("tags", [])
            if "keep_output" in tags:
                continue

            outputs = cell.get("outputs", [])
            if len(outputs) > 0:
                cells_with_outputs.append((i, len(outputs)))

    if cells_with_outputs:
        error_msg = (
            f"Notebook {relative_path} has stored outputs (should be cleared):\n"
        )
        for i, count in cells_with_outputs:
            error_msg += f"  Cell {i}: {count} output(s)\n"
        pytest.fail(error_msg)


def test_no_empty_code_cells(notebook_path, relative_path):
    """Test that notebooks have no empty code cells."""
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    empty_cells = []
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            source = cell.get("source", [])
            if isinstance(source, list):
                source_str = "".join(source)
            else:
                source_str = source or ""

            if not source_str.strip():
                empty_cells.append(i)

    if empty_cells:
        error_msg = f"Notebook {relative_path} has empty code cells: {empty_cells}"
        pytest.fail(error_msg)
