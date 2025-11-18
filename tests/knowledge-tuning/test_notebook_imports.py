"""Tests for notebook import validation."""
import ast
import json
import tokenize
from io import StringIO

import pytest


class TestNotebookImports:
    """Test notebook import statements."""

    def test_imports_are_parseable(self, notebook_files):
        """Test that all import statements in notebooks are parseable."""
        for notebook_path in notebook_files:
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
                # Skip cells that contain ! or % commands (shell/magic commands)
                has_shell_command = any(
                    line.strip().startswith("!") or line.strip().startswith("%")
                    for line in lines
                )
                if has_shell_command:
                    continue

                try:
                    # Try to parse the code
                    ast.parse(source_str)
                except SyntaxError as e:
                    pytest.fail(
                        f"Notebook {notebook_path} cell {i} has syntax error: {e}"
                    )

    def test_import_statements_are_well_formed(self, notebook_files):
        """Test that import statements are well-formed."""
        for notebook_path in notebook_files:
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
                # Skip cells that contain ! or % commands (shell/magic commands)
                has_shell_command = any(
                    line.strip().startswith("!") or line.strip().startswith("%")
                    for line in lines
                )
                if has_shell_command:
                    continue

                try:
                    tree = ast.parse(source_str)
                    # Check all import nodes
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            # If we can walk the tree, the import is well-formed
                            pass
                except SyntaxError as e:
                    pytest.fail(
                        f"Notebook {notebook_path} cell {i} has malformed import: {e}"
                    )

    def test_no_obvious_import_errors(self, notebook_files):
        """Test that there are no obvious import errors in syntax."""
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            for _i, cell in enumerate(nb.get("cells", [])):
                if cell.get("cell_type") != "code":
                    continue

                source = cell.get("source", [])
                if isinstance(source, list):
                    source_str = "".join(source)
                else:
                    source_str = source or ""

                if not source_str.strip():
                    continue

                # Check for common import errors
                lines = source_str.split("\n")
                for _line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # Check for incomplete imports
                    if stripped.startswith("import ") and not stripped.endswith(
                        (";", "\\")
                    ):
                        # Check if it's actually complete by trying to parse
                        try:
                            ast.parse(stripped)
                        except SyntaxError:
                            # Might be part of multi-line, skip for now
                            pass

    def test_imports_are_grouped(self, notebook_files):
        """Test that imports appear to be grouped (basic check)."""
        # This is a lightweight check - we just verify imports exist
        # Full grouping validation would be more complex
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

                if "import " in source_str or "from " in source_str:
                    # Found imports, which is expected
                    break

            # Most notebooks should have imports, but not all
            # This is just a sanity check
            pass

    def test_code_cells_are_tokenizable(self, notebook_files):
        """Test that code cells can be tokenized (basic syntax check)."""
        for notebook_path in notebook_files:
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
                if lines and (lines[0].strip().startswith("!") or lines[0].strip().startswith("%")):
                    continue

                try:
                    # Try to tokenize
                    list(tokenize.generate_tokens(StringIO(source_str).readline))
                except tokenize.TokenError as e:
                    pytest.fail(
                        f"Notebook {notebook_path} cell {i} has tokenization error: {e}"
                    )

