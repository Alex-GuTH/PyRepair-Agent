from pyrepair.feedback import parse_pytest_feedback
from pyrepair.models import FailureCategory, TestResult


def test_parses_assertion_failure_test_name_and_related_file() -> None:
    result = TestResult(
        exit_code=1,
        stdout="""============================= test session starts ==============================
FAILED tests/test_math.py::test_addition - assert 4 == 3
_______________________________ test_addition _______________________________

    def test_addition():
>       assert 4 == 3
E       assert 4 == 3

tests/test_math.py:5: AssertionError
""",
    )

    summary = parse_pytest_feedback(result)

    assert summary.category is FailureCategory.ASSERTION_FAILURE
    assert summary.failed_tests == ["tests/test_math.py::test_addition"]
    assert summary.related_files == ["tests/test_math.py"]


def test_parses_module_not_found_error() -> None:
    summary = parse_pytest_feedback(
        TestResult(stderr="E   ModuleNotFoundError: No module named 'missing_package'")
    )

    assert summary.category is FailureCategory.IMPORT_ERROR


def test_parses_pytest_collection_error() -> None:
    summary = parse_pytest_feedback(
        TestResult(
            stdout="""============================= test session starts ==============================
collecting ... collected 0 items / 1 error

==================================== ERRORS ====================================
_____________________ ERROR collecting tests/test_app.py ______________________
tests/test_app.py:3: in <module>
    BROKEN
E   NameError: name 'BROKEN' is not defined
=========================== short test summary info ============================
ERROR tests/test_app.py - NameError: name 'BROKEN' is not defined
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
"""
        )
    )

    assert summary.category is FailureCategory.COLLECTION_ERROR
    assert summary.related_files == ["tests/test_app.py"]


def test_parses_syntax_error() -> None:
    summary = parse_pytest_feedback(
        TestResult(stderr="E     File \"src/example.py\", line 3\nE       if True print('x')\nE               ^\nE   SyntaxError: invalid syntax")
    )

    assert summary.category is FailureCategory.SYNTAX_ERROR
    assert summary.related_files == ["src/example.py"]
    assert summary.line_hints == [3]


def test_parses_traceback_as_runtime_exception() -> None:
    summary = parse_pytest_feedback(
        TestResult(
            stdout="""Traceback (most recent call last):
  File "src/service.py", line 12, in run
    raise ValueError("bad input")
ValueError: bad input
"""
        )
    )

    assert summary.category is FailureCategory.RUNTIME_EXCEPTION
    assert summary.related_files == ["src/service.py"]
    assert summary.line_hints == [12]


def test_prioritizes_timeout() -> None:
    summary = parse_pytest_feedback(
        TestResult(timed_out=True, stderr="SyntaxError: ignored after timeout")
    )

    assert summary.category is FailureCategory.TIMEOUT
