def _tool_by_name(tools: list[dict], name: str) -> dict:
    for tool in tools:
        function = tool.get("function", {})
        if function.get("name") == name:
            return function
    raise AssertionError(f"Tool {name!r} not found")


def test_travel_tools_include_search_alternative_routes(agentic_tools_module):
    function = _tool_by_name(
        agentic_tools_module.TRAVEL_AGENT_TOOLS,
        "search_alternative_routes",
    )
    assert (
        function["description"]
        == "Search for alternative flight routes or connection options between two cities on a given date"
    )
    assert function["parameters"]["required"] == ["from_city", "to_city", "date"]
    assert (
        function["parameters"]["properties"]["from_city"]["description"]
        == "Departure city"
    )
    assert (
        function["parameters"]["properties"]["to_city"]["description"]
        == "Destination city"
    )
    assert (
        function["parameters"]["properties"]["date"]["description"]
        == "Travel date (YYYY-MM-DD)"
    )


def test_repeated_action_loop_directory_exists(agentic_evaluation_path):
    path = agentic_evaluation_path / "failure-modes" / "07_repeated_action_loop"
    assert path.is_dir(), "07_repeated_action_loop directory not found"


def test_repeated_action_loop_files_exist(agentic_evaluation_path):
    path = agentic_evaluation_path / "failure-modes" / "07_repeated_action_loop"
    assert (path / "README.md").exists(), "README.md not found"
    assert (path / "repeated_action_loop.md").exists(), (
        "repeated_action_loop.md not found"
    )


def test_repeated_action_loop_readme_mentions_self_contained_notebook(
    agentic_evaluation_path,
):
    readme = (
        agentic_evaluation_path
        / "failure-modes"
        / "07_repeated_action_loop"
        / "README.md"
    ).read_text(encoding="utf-8")
    assert "self-contained" in readme.lower()
    assert "07_repeated_action_loop.ipynb" in readme


def test_repeated_action_loop_doc_has_required_sections(agentic_evaluation_path):
    doc = (
        agentic_evaluation_path
        / "failure-modes"
        / "07_repeated_action_loop"
        / "repeated_action_loop.md"
    ).read_text(encoding="utf-8")
    for heading in [
        "## What it is",
        "## Why it matters",
        "## Scenario used",
        "## Scorers",
        "## Scorer comparison",
        "## Notebook",
    ]:
        assert heading in doc, f"Missing heading: {heading}"


def test_root_readme_lists_repeated_action_loop(agentic_evaluation_path):
    readme = (agentic_evaluation_path / "README.md").read_text(encoding="utf-8")
    assert (
        "| 7 | [Repeated Action Loop](failure-modes/07_repeated_action_loop/)" in readme
    )
    assert "07_repeated_action_loop.ipynb" in readme


def test_repeated_action_loop_notebook_has_expected_markers(
    agentic_evaluation_path, notebook_loader
):
    notebook = notebook_loader(
        agentic_evaluation_path
        / "failure-modes"
        / "07_repeated_action_loop"
        / "07_repeated_action_loop.ipynb"
    )

    markdown = "\n".join(
        "".join(cell.get("source", []))
        if isinstance(cell.get("source"), list)
        else cell.get("source", "")
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "markdown"
    )
    code = "\n".join(
        "".join(cell.get("source", []))
        if isinstance(cell.get("source"), list)
        else cell.get("source", "")
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
    )

    assert "### Prerequisites and setup" in markdown
    assert "search_alternative_routes" in code
    assert "make_judge" in code
    assert "from mlflow.genai.scorers import scorer" in code
    assert "mlflow.flush_trace_async_logging()" in code
    assert 'model="openai:/gpt-4o"' in code
