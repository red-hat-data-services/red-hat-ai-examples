#!/usr/bin/env python3
"""Runner script for push tests targeting knowledge-tuning directory."""
import sys
from pathlib import Path

import pytest

if __name__ == "__main__":
    # Get the directory containing this script
    test_dir = Path(__file__).parent
    repo_root = test_dir.parent.parent

    # Target the knowledge-tuning test directory
    test_path = test_dir

    # Create results directory
    results_dir = test_dir / "test-results"
    results_dir.mkdir(exist_ok=True)

    # Run pytest with the test directory
    # Use parallel workers for faster execution (auto-detect CPU count)
    # Generate output files for results
    exit_code = pytest.main([
        str(test_path),
        "-v",
        "--tb=short",
        "-n", "auto",  # Use pytest-xdist for parallel execution (auto-detect workers)
        "--junit-xml", str(results_dir / "junit.xml"),  # JUnit XML for CI integration
        "--html", str(results_dir / "report.html"),  # HTML report
        "--self-contained-html",  # Include CSS/JS in HTML file
        # Ensure tests run quickly - timeout handled by GitHub Actions workflow
    ])

    print(f"\n📊 Test results saved to: {results_dir}")
    print(f"   - JUnit XML: {results_dir / 'junit.xml'}")
    print(f"   - HTML Report: {results_dir / 'report.html'}")

    sys.exit(exit_code)

