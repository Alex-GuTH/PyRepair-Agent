from pyrepair.models import (
    Action,
    ActionType,
    FailureCategory,
    FailureSummary,
    TestResult,
    TestStatus,
    dataclass_to_dict,
)


def test_action_model_preserves_type_and_payload():
    action = Action(type=ActionType.READ_FILE, payload={"path": "src/app.py"})

    assert action.type is ActionType.READ_FILE
    assert action.type.value == "READ_FILE"
    assert action.payload["path"] == "src/app.py"


def test_failure_summary_defaults_to_empty_collections():
    summary = FailureSummary(category=FailureCategory.ASSERTION_FAILURE)

    assert summary.status is TestStatus.FAILED
    assert summary.failed_tests == []
    assert summary.related_files == []


def test_nested_test_result_accepts_failure_summary():
    summary = FailureSummary(
        category=FailureCategory.SYNTAX_ERROR,
        related_files=["src/app.py"],
        line_hints=[3],
    )
    result = TestResult(
        command=["python", "-m", "pytest"],
        exit_code=2,
        failure_summary=summary,
    )

    assert result.failure_summary is summary
    assert result.failure_summary.related_files == ["src/app.py"]


def test_model_serialization_uses_enum_values():
    action = Action(type=ActionType.RUN_TESTS)
    data = dataclass_to_dict(action)

    assert data["type"] == "RUN_TESTS"
    assert data["parse_status"] == "PARSED"
