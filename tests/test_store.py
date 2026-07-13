from __future__ import annotations

import json
from pathlib import Path

from pyrepair.models import (
    Action,
    ActionParseStatus,
    ActionType,
    FailureCategory,
    FailureSummary,
    RunRecord,
    RunStatus,
    RunStep,
    TestStatus,
    ToolResult,
)
from pyrepair.store import JsonlRunStore


def test_store_replays_created_run_and_appended_step(tmp_path: Path) -> None:
    store = JsonlRunStore(tmp_path / "runs")
    run = RunRecord(
        id="run-001",
        project_root="C:/projects/calculator",
        created_at="2026-07-13T10:00:00Z",
        max_rounds=2,
    )
    step = RunStep(
        run_id=run.id,
        round_index=1,
        llm_backend="mock",
        action=Action(
            type=ActionType.RUN_TESTS,
            payload={"command": ["python", "-m", "pytest", "-q"]},
            parse_status=ActionParseStatus.PARSED,
        ),
        tool_result=ToolResult(tool_name="pytest", success=True, exit_code=0),
        created_at="2026-07-13T10:01:00Z",
    )

    store.create_run(run)
    store.append_step(run.id, step)

    loaded = store.get_run(run.id)

    assert loaded.id == run.id
    assert loaded.status is RunStatus.RUNNING
    assert loaded.steps == [step]
    assert len((tmp_path / "runs" / "run-001.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_store_restores_nested_failure_summary_and_enum_values(tmp_path: Path) -> None:
    store = JsonlRunStore(tmp_path)
    run = RunRecord(id="run-002", project_root="C:/projects/example", status=RunStatus.FAILED)
    step = RunStep(
        run_id=run.id,
        round_index=0,
        feedback=FailureSummary(
            status=TestStatus.FAILED,
            category=FailureCategory.ASSERTION_FAILURE,
            failed_tests=["tests/test_example.py::test_value"],
            line_hints=[12],
        ),
    )

    store.create_run(run)
    store.append_step(run.id, step)

    loaded_step = store.get_run(run.id).steps[0]

    assert loaded_step.feedback is not None
    assert loaded_step.feedback.category is FailureCategory.ASSERTION_FAILURE
    assert loaded_step.feedback.status is TestStatus.FAILED
    assert loaded_step.feedback.line_hints == [12]
    assert store.list_runs() == [store.get_run(run.id)]


def test_store_redacts_sensitive_nested_values_before_writing(tmp_path: Path) -> None:
    store = JsonlRunStore(tmp_path)
    secret = "sk-offline-test-secret"
    run = RunRecord(id="run-003", project_root="C:/projects/secret")
    step = RunStep(
        run_id=run.id,
        round_index=1,
        action=Action(
            type=ActionType.READ_FILE,
            payload={
                "api_key": secret,
                "api_key_ref": secret,
                "OPENAI_API_KEY": secret,
                "nested": {"token": secret},
            },
        ),
    )

    store.create_run(run)
    store.append_step(run.id, step)

    stored_text = (tmp_path / "run-003.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line) for line in stored_text.splitlines()]
    payload = events[1]["step"]["action"]["payload"]

    assert secret not in stored_text
    assert payload["api_key"] == "[REDACTED]"
    assert payload["api_key_ref"] == "[REDACTED]"
    assert payload["OPENAI_API_KEY"] == "[REDACTED]"
    assert payload["nested"]["token"] == "[REDACTED]"
