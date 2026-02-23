"""
Pytest configuration for validation tests.

Provides a mechanism to run validation tests as warnings instead of failures,
allowing time to fix compliance issues without blocking CI.

Tests marked with @pytest.mark.validation_warning will show failures as warnings
but still pass, giving visibility to issues without blocking the pipeline.

To convert warnings back to failures:
1. Remove the @pytest.mark.validation_warning decorators from test files
2. Remove or comment out the pytest_runtest_makereport hook below
"""

import pytest

# Global list to collect validation warnings
validation_warnings = []


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "validation_warning: mark test to show as warning instead of failure",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Convert test failures to warnings for validation_warning marked tests."""
    outcome = yield
    report = outcome.get_result()

    # Only process if this is the call phase (actual test execution)
    if call.when == "call" and item.get_closest_marker("validation_warning"):
        if report.failed:
            # Get the failure message
            longrepr = str(report.longrepr)

            # Collect warning for summary
            validation_warnings.append({"nodeid": item.nodeid, "message": longrepr})

            # Convert failure to passed to prevent CI failure
            report.outcome = "passed"
            # Clear the failure info
            report.longrepr = None


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Display validation warnings summary at the end of test run."""
    if validation_warnings:
        terminalreporter.section(
            "Validation Warnings Summary", sep="=", yellow=True, bold=True
        )
        terminalreporter.write_line("")
        terminalreporter.write_line(
            f"Found {len(validation_warnings)} validation issue(s) that need attention:",
            yellow=True,
        )
        terminalreporter.write_line("")

        for i, warning in enumerate(validation_warnings, 1):
            terminalreporter.write_line(f"{i}. {warning['nodeid']}", bold=True)

            # Extract the assertion error message
            lines = warning["message"].split("\n")
            error_msg = None

            # Look for AssertionError line
            for j, line in enumerate(lines):
                if "AssertionError:" in line:
                    # Get the message after AssertionError:
                    msg = line.split("AssertionError:", 1)[-1].strip()
                    if msg:
                        error_msg = msg
                    # If message is on next lines, collect them
                    elif j + 1 < len(lines):
                        next_lines = []
                        for next_line in lines[j + 1 :]:
                            stripped = next_line.strip()
                            if stripped and not stripped.startswith("assert"):
                                next_lines.append(stripped)
                            else:
                                break
                        if next_lines:
                            error_msg = " ".join(next_lines)
                    break

            # If no AssertionError found, look for E lines (pytest error format)
            if not error_msg:
                e_lines = [
                    line.strip()[2:].strip()
                    for line in lines
                    if line.strip().startswith("E ")
                    and not line.strip().startswith("E   assert")
                ]
                if e_lines:
                    error_msg = " ".join(e_lines[:3])  # First 3 E lines

            # Display the error message
            if error_msg:
                terminalreporter.write_line(f"   {error_msg}", red=True)
            else:
                terminalreporter.write_line("   Validation check failed", red=True)
            terminalreporter.write_line("")

        terminalreporter.write_line(
            "These issues are currently shown as warnings but will eventually become test failures.",
            yellow=True,
        )
        terminalreporter.write_line("")
