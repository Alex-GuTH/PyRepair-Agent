from __future__ import annotations

import json
from pathlib import Path

from pyrepair.models import (
    Action,
    ActionParseStatus,
    ActionType,
    FailureCategory,
    FailureSummary,
    PatchRecord,
    RunRecord,
    RunStatus,
    RunStep,
    TestResult,
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


def test_store_replays_finished_run_status(tmp_path: Path) -> None:
    store = JsonlRunStore(tmp_path)
    run = RunRecord(id="run-finished", project_root="C:/projects/example")
    store.create_run(run)
    run.status = RunStatus.WAITING_APPROVAL
    run.updated_at = "2026-07-13T12:00:00Z"
    run.final_summary = "Approval is required."

    store.finish_run(run)

    replayed_run = store.get_run(run.id)

    assert replayed_run.status is RunStatus.WAITING_APPROVAL
    assert replayed_run.updated_at == "2026-07-13T12:00:00Z"
    assert replayed_run.final_summary == "Approval is required."


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


def test_store_redacts_secrets_in_unstructured_text_fields(tmp_path: Path) -> None:
    store = JsonlRunStore(tmp_path)
    secret = "sk-unstructured-secret-123"
    run = RunRecord(id="run-004", project_root="C:/projects/secret")
    step = RunStep(
        run_id=run.id,
        round_index=1,
        context_summary=f"Use OPENAI_API_KEY = {secret}",
        action=Action(
            type=ActionType.APPLY_PATCH,
            raw_model_output=f'{{"api_key": "{secret}"}}',
        ),
        tool_result=ToolResult(
            tool_name="pytest",
            stdout_summary=f"stdout leaked {secret}",
            stderr_summary=f"stderr has OPENAI_API_KEY={secret}",
            test_result=TestResult(stdout=f"raw stdout {secret}", stderr=f"raw stderr {secret}"),
            patch_record=PatchRecord(diff=f"+API_KEY = '{secret}'\n"),
        ),
        feedback=FailureSummary(message=f"secret token: {secret}"),
    )

    store.create_run(run)
    store.append_step(run.id, step)

    stored_text = (tmp_path / "run-004.jsonl").read_text(encoding="utf-8")

    assert secret not in stored_text
    assert "[REDACTED]" in stored_text


def test_store_redacts_common_auth_headers_and_key_assignments(tmp_path: Path) -> None:
    store = JsonlRunStore(tmp_path)
    secret = "rk-live-provider-secret-456"
    run = RunRecord(id="run-005", project_root="C:/projects/secret")
    step = RunStep(
        run_id=run.id,
        round_index=1,
        context_summary=f"Authorization: Bearer {secret}",
        action=Action(
            type=ActionType.RUN_TESTS,
            raw_model_output=f"X-API-Key: {secret}",
        ),
        tool_result=ToolResult(
            tool_name="pytest",
            stderr_summary=f"PROVIDER_KEY={secret}",
        ),
    )

    store.create_run(run)
    store.append_step(run.id, step)

    stored_text = (tmp_path / "run-005.jsonl").read_text(encoding="utf-8")

    assert secret not in stored_text
    assert "[REDACTED]" in stored_text


def test_store_redacts_access_key_and_non_bearer_authorization(tmp_path: Path) -> None:
    store = JsonlRunStore(tmp_path)
    secret = "rk-live-provider-secret-789"
    run = RunRecord(id="run-006", project_root="C:/projects/secret")
    step = RunStep(
        run_id=run.id,
        round_index=1,
        context_summary=f"Authorization: Token {secret}",
        action=Action(
            type=ActionType.READ_FILE,
            payload={"access_key": secret},
            raw_model_output=f'{{"access_key":"{secret}"}}',
        ),
    )

    store.create_run(run)
    store.append_step(run.id, step)

    stored_text = (tmp_path / "run-006.jsonl").read_text(encoding="utf-8")

    assert secret not in stored_text
    assert "[REDACTED]" in stored_text
