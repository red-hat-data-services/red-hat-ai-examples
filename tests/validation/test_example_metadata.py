"""
Example metadata validation tests.

Tests that validate example.yaml metadata files:
- Presence of metadata files
- Valid YAML syntax
- Required fields present
- Schema validation
- Predefined value constraints
"""

from pathlib import Path

import pytest
import yaml

# Predefined vocabularies
VALID_STATUSES = {"community", "validated"}
VALID_COMPLEXITIES = {"beginner", "intermediate", "advanced"}
VALID_TAGS = {
    "fine-tuning",
    "knowledge-tuning",
    "compression",
    "quantization",
    "RAG",
    "evaluation",
    "distributed-training",
    "pipeline",
    "inference",
    "continual-learning",
}
VALID_USE_CASES = {
    "model-compression",
    "model-fine-tuning",
    "knowledge-injection",
    "continual-learning",
    "domain-customization",
    "model-evaluation",
    "data-generation",
}
VALID_RHOAI_COMPONENTS = {
    "workbench",
    "data-science-pipelines",
    "training-operator",
    "model-serving",
    "kserve",
}


def pytest_generate_tests(metafunc):
    """Generate test parameters from all example directories."""
    if "example_path" in metafunc.fixturenames:
        repo_root = Path(__file__).parent.parent.parent
        examples_dir = repo_root / "examples"

        # Find all example directories (immediate subdirs of examples/)
        example_dirs = [
            d
            for d in examples_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        metafunc.parametrize("example_path", example_dirs)


@pytest.mark.validation_warning
def test_example_metadata_exists(example_path):
    """Test that example.yaml exists in example directory."""
    metadata_file = example_path / "example.yaml"
    assert metadata_file.exists(), (
        f"Missing example.yaml in {example_path.name}. "
        f"Create example.yaml with required metadata. "
        f"See docs/METADATA_SCHEMA.md for details."
    )


def test_example_metadata_is_valid_yaml(example_path):
    """Test that example.yaml is valid YAML."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    try:
        with open(metadata_file) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "Metadata must be a dictionary"
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML in {metadata_file}: {e}")


def test_required_fields_present(example_path):
    """Test that required metadata fields are present."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    metadata = data.get("metadata", {})

    # Required top-level fields (simplified schema)
    required_fields = [
        "title",
        "description",
        "status",
        "components",
    ]

    missing = [field for field in required_fields if field not in metadata]
    assert not missing, (
        f"Missing required fields in {metadata_file}: {missing}. "
        f"See docs/METADATA_SCHEMA.md for required fields."
    )


def test_status_is_valid(example_path):
    """Test that status field has valid value."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    status = data.get("metadata", {}).get("status")
    assert status in VALID_STATUSES, (
        f"Invalid status '{status}' in {metadata_file}. "
        f"Must be one of: {VALID_STATUSES}"
    )


def test_title_is_not_empty(example_path):
    """Test that title is not empty."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    title = data.get("metadata", {}).get("title", "")
    assert title and title.strip(), f"Title cannot be empty in {metadata_file}"


def test_description_is_not_empty(example_path):
    """Test that description is not empty."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    description = data.get("metadata", {}).get("description", "")
    assert description and description.strip(), (
        f"Description cannot be empty in {metadata_file}"
    )


def test_rhoai_components_are_valid(example_path):
    """Test that RHOAI components are from predefined list."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    components = data.get("metadata", {}).get("components", {}).get("rhoai", [])
    assert isinstance(components, list), (
        f"RHOAI components must be a list in {metadata_file}"
    )
    assert len(components) > 0, (
        f"At least one RHOAI component is required in {metadata_file}"
    )

    invalid = set(components) - VALID_RHOAI_COMPONENTS
    assert not invalid, (
        f"Invalid RHOAI components in {metadata_file}: {invalid}. "
        f"Must be from: {VALID_RHOAI_COMPONENTS}"
    )


# Optional field validation tests (only validate if present)


def test_hardware_fields_valid_if_present(example_path):
    """Test that hardware fields are valid if present."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    hardware = data.get("metadata", {}).get("hardware")
    if hardware is None:
        pytest.skip("Hardware section not present (optional)")

    # If hardware is present, gpu.required and multi_node are required
    gpu = hardware.get("gpu", {})
    assert "required" in gpu, (
        f"hardware.gpu.required is required when hardware section is present "
        f"in {metadata_file}"
    )
    assert isinstance(gpu.get("required"), bool), (
        f"hardware.gpu.required must be boolean in {metadata_file}"
    )

    assert "multi_node" in hardware, (
        f"hardware.multi_node is required when hardware section is present "
        f"in {metadata_file}"
    )
    assert isinstance(hardware.get("multi_node"), bool), (
        f"hardware.multi_node must be boolean in {metadata_file}"
    )

    # Validate optional hardware fields if present
    if gpu.get("count") is not None:
        assert isinstance(gpu.get("count"), int), (
            f"hardware.gpu.count must be integer in {metadata_file}"
        )

    if gpu.get("memory_per_gpu") is not None:
        assert isinstance(gpu.get("memory_per_gpu"), str), (
            f"hardware.gpu.memory_per_gpu must be string in {metadata_file}"
        )


def test_duration_estimate_fields_valid_if_present(example_path):
    """Test that duration_estimate fields are valid if present."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    duration = data.get("metadata", {}).get("duration_estimate")
    if duration is None:
        pytest.skip("Duration estimate section not present (optional)")

    # If duration_estimate is present, execution and total are required
    assert "execution" in duration, (
        f"duration_estimate.execution is required when duration_estimate section "
        f"is present in {metadata_file}"
    )
    assert "total" in duration, (
        f"duration_estimate.total is required when duration_estimate section "
        f"is present in {metadata_file}"
    )


def test_complexity_is_valid_if_present(example_path):
    """Test that complexity field has valid value if present."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    complexity = data.get("metadata", {}).get("complexity")
    if complexity is None:
        pytest.skip("Complexity not present (optional)")

    assert complexity in VALID_COMPLEXITIES, (
        f"Invalid complexity '{complexity}' in {metadata_file}. "
        f"Must be one of: {VALID_COMPLEXITIES}"
    )


def test_tags_are_valid_if_present(example_path):
    """Test that all tags are from predefined list if present."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    tags = data.get("metadata", {}).get("tags")
    if tags is None:
        pytest.skip("Tags not present (optional)")

    assert isinstance(tags, list), f"Tags must be a list in {metadata_file}"

    invalid_tags = set(tags) - VALID_TAGS
    assert not invalid_tags, (
        f"Invalid tags in {metadata_file}: {invalid_tags}. Must be from: {VALID_TAGS}"
    )


def test_use_case_is_valid_if_present(example_path):
    """Test that use_case is from predefined list if present."""
    metadata_file = example_path / "example.yaml"
    if not metadata_file.exists():
        pytest.skip(f"No metadata file in {example_path.name}")

    with open(metadata_file) as f:
        data = yaml.safe_load(f)

    use_case = data.get("metadata", {}).get("use_case")
    if use_case is None:
        pytest.skip("Use case not present (optional)")

    assert use_case in VALID_USE_CASES, (
        f"Invalid use_case '{use_case}' in {metadata_file}. "
        f"Must be one of: {VALID_USE_CASES}"
    )
