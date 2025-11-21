#!/usr/bin/env python3
"""Runner script for repo-wide notebook format checks."""

import sys
from pathlib import Path

import pytest

SUITE_NAME = "format_checks"


def _results_dir() -> Path:
    """Return the shared test-results directory for this suite."""
    tests_root = Path(__file__).resolve().parents[1]
    results_dir = tests_root / "test-results" / SUITE_NAME
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def main() -> int:
    """Execute pytest for the format_checks suite."""
    test_dir = Path(__file__).parent
    results_dir = _results_dir()

    return pytest.main([
        str(test_dir),
        "-v",
        "--tb=short",
        "-n",
        "auto",
        "--junit-xml",
        str(results_dir / "junit.xml"),
        "--html",
        str(results_dir / "report.html"),
        "--self-contained-html",
    ])


if __name__ == "__main__":
    exit_code = main()

    results_dir = _results_dir()
    print(f"\n📊 Format check results saved to: {results_dir}")
    print(f"   - JUnit XML: {results_dir / 'junit.xml'}")
    print(f"   - HTML Report: {results_dir / 'report.html'}")

    sys.exit(exit_code)
