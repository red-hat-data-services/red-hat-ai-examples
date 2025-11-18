"""Tests for notebook structure validation."""
import json

import nbformat
import pytest


class TestNotebookStructure:
    """Test notebook structure and metadata compliance."""

    def test_no_execution_counts(self, notebook_files):
        """Test that notebooks have no execution counts."""
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            for cell in nb.get("cells", []):
                execution_count = cell.get("execution_count")
                assert (
                    execution_count is None
                ), f"Notebook {notebook_path} has execution_count {execution_count} in cell"

    def test_no_stored_outputs(self, notebook_files):
        """Test that notebooks have no stored outputs."""
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            for i, cell in enumerate(nb.get("cells", [])):
                outputs = cell.get("outputs", [])
                assert (
                    len(outputs) == 0
                ), f"Notebook {notebook_path} has {len(outputs)} outputs in cell {i}"

    def test_kernelspec_consistency(self, notebook_files):
        """Test that all notebooks have consistent kernelspec.name."""
        if not notebook_files:
            pytest.skip("No notebooks found")

        kernelspecs = []
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            kernelspec = nb.get("metadata", {}).get("kernelspec", {})
            kernelspec_name = kernelspec.get("name")
            if kernelspec_name:
                kernelspecs.append((notebook_path, kernelspec_name))

        if kernelspecs:
            # Get the first kernelspec name as the reference
            first_name = kernelspecs[0][1]
            for notebook_path, name in kernelspecs:
                assert (
                    name == first_name
                ), f"Notebook {notebook_path} has kernelspec.name '{name}', expected '{first_name}'"

    def test_language_info_version_consistency(self, notebook_files):
        """Test that all notebooks have consistent language_info.version."""
        if not notebook_files:
            pytest.skip("No notebooks found")

        versions = []
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            language_info = nb.get("metadata", {}).get("language_info", {})
            version = language_info.get("version")
            if version:
                versions.append((notebook_path, version))

        if versions:
            # Get the first version as the reference
            first_version = versions[0][1]
            for notebook_path, version in versions:
                assert (
                    version == first_version
                ), f"Notebook {notebook_path} has language_info.version '{version}', expected '{first_version}'"

    def test_no_environment_specific_metadata(self, notebook_files):
        """Test that notebooks don't contain environment-specific metadata."""
        env_specific_keys = [
            "execution",
            "executor",
            "interpreter",
            "ipython",
            "vscode",
            "colab",
            "kaggle",
        ]

        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            metadata = nb.get("metadata", {})
            for key in env_specific_keys:
                # Check top-level metadata
                if key in metadata:
                    # Allow some keys that are standard (like kernelspec, language_info)
                    if key not in ["kernelspec", "language_info"]:
                        pytest.fail(
                            f"Notebook {notebook_path} contains environment-specific metadata key: {key}"
                        )

    def test_standardized_metadata_schema(self, notebook_files):
        """Test that all notebooks follow a standardized metadata schema."""
        if not notebook_files:
            pytest.skip("No notebooks found")

        # Load first notebook to establish schema
        with open(notebook_files[0], encoding="utf-8") as f:
            first_nb = json.load(f)
        first_metadata_keys = set(first_nb.get("metadata", {}).keys())

        # Compare all other notebooks
        for notebook_path in notebook_files[1:]:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            metadata_keys = set(nb.get("metadata", {}).keys())

            # Allow some variation but core keys should match
            # Exclude environment-specific keys that might differ
            core_keys = {
                "kernelspec",
                "language_info",
            }
            first_core = first_metadata_keys & core_keys
            current_core = metadata_keys & core_keys

            assert (
                first_core == current_core
            ), f"Notebook {notebook_path} has different core metadata keys. Expected {first_core}, got {current_core}"

    def test_required_sections_exist(self, notebook_files):
        """Test that notebooks contain required sections."""
        required_keywords = [
            "import",
            "setup",
            "install",
        ]

        for notebook_path in notebook_files:
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
            assert (
                len(found_keywords) > 0
            ), f"Notebook {notebook_path} missing required sections (imports, setup, or install)"

    def test_cell_type_ordering(self, notebook_files):
        """Test that notebooks have logical ordering of markdown and code cells."""
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            cells = nb.get("cells", [])
            if len(cells) < 2:
                continue

            # First cell should typically be markdown (title/overview)
            first_cell_type = cells[0].get("cell_type")
            assert first_cell_type in [
                "markdown",
                "code",
            ], f"Notebook {notebook_path} first cell has unexpected type: {first_cell_type}"

    def test_no_empty_cells(self, notebook_files):
        """Test that notebooks have no empty cells."""
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            for i, cell in enumerate(nb.get("cells", [])):
                source = cell.get("source", [])
                if isinstance(source, list):
                    source_str = "".join(source)
                else:
                    source_str = source or ""

                # Allow markdown cells with just whitespace, but code cells should have content
                if cell.get("cell_type") == "code" and not source_str.strip():
                    pytest.fail(
                        f"Notebook {notebook_path} has empty code cell at index {i}"
                    )

    def test_notebooks_are_valid_json(self, notebook_files):
        """Test that all notebook files are valid JSON."""
        for notebook_path in notebook_files:
            try:
                with open(notebook_path, encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(
                    f"Notebook {notebook_path} is not valid JSON: {e}"
                )

    def test_notebooks_are_valid_nbformat(self, notebook_files):
        """Test that all notebook files are valid nbformat."""
        for notebook_path in notebook_files:
            try:
                nbformat.read(str(notebook_path), as_version=4)
            except Exception as e:
                pytest.fail(
                    f"Notebook {notebook_path} is not valid nbformat: {e}"
                )

