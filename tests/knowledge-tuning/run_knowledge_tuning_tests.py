#!/usr/bin/env python3
"""Runner script for knowledge-tuning specific tests."""

import sys
from pathlib import Path

import pytest

SUITE_NAME = "knowledge-tuning"


def _results_dir() -> Path:
    """Return the shared test-results directory for this suite."""
    tests_root = Path(__file__).resolve().parents[1]
    results_dir = tests_root / "test-results" / SUITE_NAME
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


if __name__ == "__main__":
    # Get the directory containing this script
    test_dir = Path(__file__).parent

    # Target the knowledge-tuning test directory
    test_path = test_dir

    results_dir = _results_dir()

    # Run pytest with the test directory
    # Use parallel workers for faster execution (auto-detect CPU count)
    # Generate output files for results
    exit_code = pytest.main([
        str(test_path),
        "-v",
        "--tb=short",
        "-n",
        "auto",  # Use pytest-xdist for parallel execution (auto-detect workers)
        "--junit-xml",
        str(results_dir / "junit.xml"),  # JUnit XML for CI integration
        "--html",
        str(results_dir / "report.html"),  # HTML report
        "--self-contained-html",  # Include CSS/JS in HTML file
        # Ensure tests run quickly - timeout handled by GitHub Actions workflow
    ])

    print(f"\n📊 Knowledge-tuning test results saved to: {results_dir}")
    print(f"   - JUnit XML: {results_dir / 'junit.xml'}")
    print(f"   - HTML Report: {results_dir / 'report.html'}")

    sys.exit(exit_code)
