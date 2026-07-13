from __future__ import annotations

import re

from pyrepair.models import FailureCategory, FailureSummary, TestResult, TestStatus


_FAILED_TEST_PATTERN = re.compile(r"^FAILED\s+(\S+)", re.MULTILINE)
_TRACEBACK_FILE_PATTERN = re.compile(r'^\s*(?:E\s+)?File "([^"]+)", line (\d+)', re.MULTILINE)
_PYTEST_FILE_PATTERN = re.compile(r"^([^\n\r:]+\.py):(\d+):", re.MULTILINE)


def parse_pytest_feedback(test_result: TestResult) -> FailureSummary:
    """Classify pytest feedback and extract only explicit failure locations."""
    output = "\n".join(part for part in (test_result.stdout, test_result.stderr) if part)
    category = _classify(test_result, output)
    failed_tests = _unique(_FAILED_TEST_PATTERN.findall(output))
    related_files, line_hints = _extract_locations(output, failed_tests)

    return FailureSummary(
        status=TestStatus.TIMEOUT if test_result.timed_out else TestStatus.FAILED,
        category=category,
        failed_tests=failed_tests,
        related_files=related_files,
        traceback_excerpt=output[-2000:],
        line_hints=line_hints,
        message=_last_nonempty_line(output),
    )


def _classify(test_result: TestResult, output: str) -> FailureCategory:
    if test_result.timed_out:
        return FailureCategory.TIMEOUT
    if "SyntaxError" in output:
        return FailureCategory.SYNTAX_ERROR
    if "ImportError" in output or "ModuleNotFoundError" in output:
        return FailureCategory.IMPORT_ERROR
    if "E       assert" in output:
        return FailureCategory.ASSERTION_FAILURE
    if "Traceback" in output:
        return FailureCategory.RUNTIME_EXCEPTION
    return FailureCategory.UNKNOWN_FAILURE


def _extract_locations(output: str, failed_tests: list[str]) -> tuple[list[str], list[int]]:
    files = [test_name.split("::", 1)[0] for test_name in failed_tests if "::" in test_name]
    lines: list[int] = []

    for path, line_number in _TRACEBACK_FILE_PATTERN.findall(output):
        files.append(path)
        lines.append(int(line_number))
    for path, line_number in _PYTEST_FILE_PATTERN.findall(output):
        files.append(path)
        lines.append(int(line_number))

    return _unique(files), _unique(lines)


def _last_nonempty_line(output: str) -> str:
    for line in reversed(output.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def _unique(values: list[str] | list[int]) -> list[str] | list[int]:
    return list(dict.fromkeys(values))
