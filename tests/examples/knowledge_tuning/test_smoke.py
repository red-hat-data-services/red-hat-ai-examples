"""
Smoke tests for knowledge-tuning example notebooks.

These tests perform basic smoke testing on the knowledge-tuning notebooks:
1. Check that notebooks can be parsed
2. Verify expected structure and key cells exist
3. Validate environment variable usage
4. Check for required imports and dependencies
5. Ensure consistency across notebooks (Python version, etc.)
"""

import json

import pytest
from nbformat import read


class TestKnowledgeTuningStructure:
    """Test knowledge-tuning example structure."""

    def test_knowledge_tuning_directory_exists(self, knowledge_tuning_path):
        """Test that knowledge-tuning directory exists."""
        assert knowledge_tuning_path.is_dir()

    def test_readme_exists(self, knowledge_tuning_path):
        """Test that README.md exists in knowledge-tuning directory."""
        readme = knowledge_tuning_path / "README.md"
        assert readme.exists(), "README.md not found"

    def test_env_example_exists(self, knowledge_tuning_path):
        """Test that .env.example exists."""
        env_example = knowledge_tuning_path / ".env.example"
        assert env_example.exists(), ".env.example not found"

    @pytest.mark.parametrize(
        "step_dir",
        [
            "00_Setup",
            "01_Base_Model_Evaluation",
            "02_Data_Processing",
            "03_Knowledge_Generation",
            "04_Knowledge_Mixing",
            "05_Model_Training",
            "06_Evaluation",
        ],
    )
    def test_step_directories_exist(self, knowledge_tuning_path, step_dir):
        """Test that all step directories exist."""
        step_path = knowledge_tuning_path / step_dir
        assert step_path.is_dir(), f"{step_dir} directory not found"

    @pytest.mark.parametrize(
        "step_dir",
        [
            "01_Base_Model_Evaluation",
            "02_Data_Processing",
            "03_Knowledge_Generation",
            "04_Knowledge_Mixing",
            "05_Model_Training",
            "06_Evaluation",
        ],
    )
    def test_step_has_pyproject_toml(self, knowledge_tuning_path, step_dir):
        """Test that each step has a pyproject.toml file."""
        pyproject = knowledge_tuning_path / step_dir / "pyproject.toml"
        assert pyproject.exists(), f"pyproject.toml not found in {step_dir}"


class TestBaseModelEvaluationNotebook:
    """Smoke tests for Base Model Evaluation notebook."""

    @pytest.fixture
    def notebook_path(self, knowledge_tuning_path):
        """Get notebook path."""
        path = (
            knowledge_tuning_path
            / "01_Base_Model_Evaluation"
            / "Base_Model_Evaluation.ipynb"
        )
        assert path.exists(), "Base_Model_Evaluation.ipynb not found"
        return path

    @pytest.fixture
    def notebook(self, notebook_path):
        """Load the notebook."""
        return read(str(notebook_path), as_version=4)

    def test_notebook_has_cells(self, notebook):
        """Test that notebook has cells."""
        assert len(notebook.cells) > 0

    def test_notebook_has_markdown_cells(self, notebook):
        """Test that notebook has markdown documentation."""
        markdown_cells = [c for c in notebook.cells if c.cell_type == "markdown"]
        assert len(markdown_cells) > 0, "No markdown cells found"

    def test_notebook_has_code_cells(self, notebook):
        """Test that notebook has code cells."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        assert len(code_cells) > 0, "No code cells found"

    def test_imports_transformers(self, notebook):
        """Test that notebook imports transformers library."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        all_code = "\n".join(cell.source for cell in code_cells)
        assert "transformers" in all_code, "transformers not imported"

    def test_imports_torch(self, notebook):
        """Test that notebook imports torch."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        all_code = "\n".join(cell.source for cell in code_cells)
        assert "torch" in all_code, "torch not imported"

    def test_uses_env_variables(self, notebook):
        """Test that notebook uses environment variables."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        all_code = "\n".join(cell.source for cell in code_cells)
        assert "load_dotenv" in all_code or "os.getenv" in all_code, (
            "Environment variables not used"
        )

    def test_defines_model_name(self, notebook):
        """Test that notebook defines MODEL_NAME."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        all_code = "\n".join(cell.source for cell in code_cells)
        assert "MODEL_NAME" in all_code, "MODEL_NAME not defined"

    def test_has_overview_section(self, notebook):
        """Test that notebook has overview section."""
        markdown_cells = [c for c in notebook.cells if c.cell_type == "markdown"]
        all_markdown = "\n".join(cell.source.lower() for cell in markdown_cells)
        assert "overview" in all_markdown, "No overview section found"


class TestDataProcessingNotebook:
    """Smoke tests for Data Processing notebook."""

    @pytest.fixture
    def notebook_path(self, knowledge_tuning_path):
        """Get notebook path."""
        path = knowledge_tuning_path / "02_Data_Processing" / "Data_Processing.ipynb"
        assert path.exists(), "Data_Processing.ipynb not found"
        return path

    @pytest.fixture
    def notebook(self, notebook_path):
        """Load the notebook."""
        return read(str(notebook_path), as_version=4)

    def test_notebook_has_cells(self, notebook):
        """Test that notebook has cells."""
        assert len(notebook.cells) > 0

    def test_notebook_has_code_cells(self, notebook):
        """Test that notebook has code cells."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        assert len(code_cells) > 0, "No code cells found"

    def test_uses_pathlib(self, notebook):
        """Test that notebook uses pathlib for paths."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        all_code = "\n".join(cell.source for cell in code_cells)
        assert "Path" in all_code, "pathlib.Path not used"


class TestKnowledgeGenerationNotebook:
    """Smoke tests for Knowledge Generation notebook."""

    @pytest.fixture
    def notebook_path(self, knowledge_tuning_path):
        """Get notebook path."""
        path = (
            knowledge_tuning_path
            / "03_Knowledge_Generation"
            / "Knowledge_Generation.ipynb"
        )
        assert path.exists(), "Knowledge_Generation.ipynb not found"
        return path

    @pytest.fixture
    def notebook(self, notebook_path):
        """Load the notebook."""
        return read(str(notebook_path), as_version=4)

    def test_notebook_has_cells(self, notebook):
        """Test that notebook has cells."""
        assert len(notebook.cells) > 0

    def test_notebook_has_code_cells(self, notebook):
        """Test that notebook has code cells."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        assert len(code_cells) > 0, "No code cells found"


class TestKnowledgeMixingNotebook:
    """Smoke tests for Knowledge Mixing notebook."""

    @pytest.fixture
    def notebook_path(self, knowledge_tuning_path):
        """Get notebook path."""
        path = knowledge_tuning_path / "04_Knowledge_Mixing" / "Knowledge_Mixing.ipynb"
        assert path.exists(), "Knowledge_Mixing.ipynb not found"
        return path

    @pytest.fixture
    def notebook(self, notebook_path):
        """Load the notebook."""
        return read(str(notebook_path), as_version=4)

    def test_notebook_has_cells(self, notebook):
        """Test that notebook has cells."""
        assert len(notebook.cells) > 0


class TestModelTrainingNotebook:
    """Smoke tests for Model Training notebook."""

    @pytest.fixture
    def notebook_path(self, knowledge_tuning_path):
        """Get notebook path."""
        path = knowledge_tuning_path / "05_Model_Training" / "Model_Training.ipynb"
        assert path.exists(), "Model_Training.ipynb not found"
        return path

    @pytest.fixture
    def notebook(self, notebook_path):
        """Load the notebook."""
        return read(str(notebook_path), as_version=4)

    def test_notebook_has_cells(self, notebook):
        """Test that notebook has cells."""
        assert len(notebook.cells) > 0

    def test_notebook_has_code_cells(self, notebook):
        """Test that notebook has code cells."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        assert len(code_cells) > 0, "No code cells found"


class TestEvaluationNotebook:
    """Smoke tests for Evaluation notebook."""

    @pytest.fixture
    def notebook_path(self, knowledge_tuning_path):
        """Get notebook path."""
        path = knowledge_tuning_path / "06_Evaluation" / "Evaluation.ipynb"
        assert path.exists(), "Evaluation.ipynb not found"
        return path

    @pytest.fixture
    def notebook(self, notebook_path):
        """Load the notebook."""
        return read(str(notebook_path), as_version=4)

    def test_notebook_has_cells(self, notebook):
        """Test that notebook has cells."""
        assert len(notebook.cells) > 0

    def test_notebook_has_code_cells(self, notebook):
        """Test that notebook has code cells."""
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        assert len(code_cells) > 0, "No code cells found"


class TestKnowledgeTuningConsistency:
    """Tests for consistency across knowledge-tuning notebooks."""

    def test_language_info_version_consistency(self, notebook_files):
        """Ensure language_info.version stays consistent across knowledge-tuning notebooks."""
        if not notebook_files:
            pytest.skip("No notebooks found")

        versions = []
        for notebook_path in notebook_files:
            with open(notebook_path, encoding="utf-8") as f:
                nb = json.load(f)

            language_info = nb.get("metadata", {}).get("language_info", {})
            version = language_info.get("version")
            if version:
                versions.append((notebook_path.name, version))

        if versions:
            first_version = versions[0][1]
            for notebook_name, version in versions:
                assert version == first_version, (
                    f"Notebook {notebook_name} has language_info.version '{version}', "
                    f"expected '{first_version}'"
                )

    def test_all_notebooks_found(self, notebook_files):
        """Test that we found notebooks in knowledge-tuning."""
        assert len(notebook_files) > 0, "No notebooks found in knowledge-tuning"
        print(f"\nFound {len(notebook_files)} notebooks in knowledge-tuning")

    def test_all_pyproject_files_found(self, pyproject_files):
        """Test that we found pyproject.toml files in knowledge-tuning."""
        assert len(pyproject_files) > 0, "No pyproject.toml files found"
        print(
            f"\nFound {len(pyproject_files)} pyproject.toml files in knowledge-tuning"
        )
