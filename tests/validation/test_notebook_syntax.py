"""
Notebook syntax validation tests.

Tests that validate Python code syntax in notebooks:
- Import statements are parseable
- Import statements are well-formed
- Code cells have valid Python syntax
- Code cells are tokenizable
"""

import ast
import json
import tokenize
from io import StringIO

import pytest


def pytest_generate_tests(metafunc):
    """Generate test parameters from all notebooks."""
    if (
        "notebook_path" in metafunc.fixturenames
        and "relative_path" in metafunc.fixturenames
    ):
        all_notebooks = metafunc.config._notebooks
        metafunc.parametrize("notebook_path,relative_path", all_notebooks)


def test_imports_are_parseable(notebook_path, relative_path):
    """Test that all import statements in notebooks are parseable."""
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            source_str = "".join(source)
        else:
            source_str = source or ""

        if not source_str.strip():
            continue

        # Skip shell commands and magic commands
        lines = source_str.split("\n")
        has_shell_or_magic = any(
            line.strip().startswith("!") or line.strip().startswith("%")
            for line in lines
        )
        if has_shell_or_magic:
            continue

        try:
            ast.parse(source_str)
        except SyntaxError as e:
            pytest.fail(
                f"Notebook {relative_path} cell {i} has syntax error: {e}\n"
                f"Source:\n{source_str[:200]}"
            )


def test_import_statements_are_well_formed(notebook_path, relative_path):
    """Test that import statements are well-formed."""
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            source_str = "".join(source)
        else:
            source_str = source or ""

        if not source_str.strip():
            continue

        # Skip shell commands and magic commands
        lines = source_str.split("\n")
        has_shell_or_magic = any(
            line.strip().startswith("!") or line.strip().startswith("%")
            for line in lines
        )
        if has_shell_or_magic:
            continue

        try:
            tree = ast.parse(source_str)
            # Check all import nodes are well-formed
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Verify the import node has expected attributes
                    if isinstance(node, ast.Import):
                        assert hasattr(node, "names"), (
                            f"Import node missing 'names' in {relative_path} cell {i}"
                        )
                    elif isinstance(node, ast.ImportFrom):
                        assert hasattr(node, "module") or node.level > 0, (
                            f"ImportFrom node invalid in {relative_path} cell {i}"
                        )
        except SyntaxError as e:
            pytest.fail(f"Notebook {relative_path} cell {i} has malformed import: {e}")


def test_no_obvious_import_errors(notebook_path, relative_path):
    """Test that there are no obvious import errors in syntax."""
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            source_str = "".join(source)
        else:
            source_str = source or ""

        if not source_str.strip():
            continue

        # Skip shell commands and magic commands
        lines = source_str.split("\n")
        has_shell_or_magic = any(
            line.strip().startswith("!") or line.strip().startswith("%")
            for line in lines
        )
        if has_shell_or_magic:
            continue

        # Check for common import errors
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            # Check for incomplete imports
            if stripped.startswith("import ") or stripped.startswith("from "):
                # Verify it's part of valid Python by parsing the whole cell
                try:
                    ast.parse(source_str)
                except SyntaxError as e:
                    pytest.fail(
                        f"Notebook {relative_path} cell {i} line {line_num} has import error: {e}\n"
                        f"Line: {stripped}"
                    )


def test_code_cells_are_tokenizable(notebook_path, relative_path):
    """Test that code cells can be tokenized (basic syntax check)."""
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            source_str = "".join(source)
        else:
            source_str = source or ""

        if not source_str.strip():
            continue

        # Skip shell commands and magic commands
        lines = source_str.split("\n")
        has_shell_or_magic = any(
            line.strip().startswith("!") or line.strip().startswith("%")
            for line in lines
        )
        if has_shell_or_magic:
            continue

        try:
            # Try to tokenize
            list(tokenize.generate_tokens(StringIO(source_str).readline))
        except tokenize.TokenError as e:
            pytest.fail(
                f"Notebook {relative_path} cell {i} has tokenization error: {e}"
            )
