"""Knowledge-tuning specific notebook structure checks."""

import json

import pytest


class TestKnowledgeNotebookStructure:
    """Tests targeting knowledge-tuning notebooks only."""

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
                versions.append((notebook_path, version))

        if versions:
            first_version = versions[0][1]
            for notebook_path, version in versions:
                assert version == first_version, (
                    f"Notebook {notebook_path} has language_info.version '{version}', "
                    f"expected '{first_version}'"
                )
