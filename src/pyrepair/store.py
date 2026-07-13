from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pyrepair.models import (
    Action,
    ActionParseStatus,
    ActionType,
    FailureCategory,
    FailureSummary,
    GuardrailDecision,
    GuardrailDecisionType,
    PatchRecord,
    RunRecord,
    RunStatus,
    RunStep,
    TestResult,
    TestStatus,
    ToolResult,
    dataclass_to_dict,
)


_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "credential",
    "private_key",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(Authorization\s*:\s*Bearer\s+)[^'\"\s,;]+"),
    re.compile(r"(?i)([A-Z0-9_-]*KEY\s*[:=]\s*)['\"]?[^'\"\s,;]+"),
    re.compile(
        r"(?i)(OPENAI_API_KEY|API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE_KEY)\s*=\s*['\"]?[^'\"\s,;]+"
    ),
    re.compile(
        r"(?i)([\"']?(?:api_key|apikey|token|secret|password|credential|private_key)[\"']?\s*:\s*[\"'])[^\"']+([\"'])"
    ),
    re.compile(
        r"(?i)((?:api_key|apikey|token|secret|password|credential|private_key)\s*:\s*)[^,\s;]+"
    ),
)


class JsonlRunStore:
    """Append-only, per-run JSONL persistence for run records and steps."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir

    def create_run(self, run: RunRecord) -> None:
        path = self._path_for(run.id)
        if path.exists():
            raise FileExistsError(f"run already exists: {run.id}")
        self._append_event(path, {"event": "run-created", "run": dataclass_to_dict(run)})

    def append_step(self, run_id: str, step: RunStep) -> None:
        if step.run_id != run_id:
            raise ValueError("step run_id must match the target run_id")
        path = self._path_for(run_id)
        if not path.exists():
            raise FileNotFoundError(f"run does not exist: {run_id}")
        self._append_event(path, {"event": "step-appended", "step": dataclass_to_dict(step)})

    def get_run(self, run_id: str) -> RunRecord:
        path = self._path_for(run_id)
        if not path.exists():
            raise FileNotFoundError(f"run does not exist: {run_id}")

        run: RunRecord | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["event"] == "run-created":
                run = _run_record_from_dict(event["run"])
            elif event["event"] == "step-appended":
                if run is None:
                    raise ValueError(f"step event precedes run creation: {run_id}")
                run.steps.append(_run_step_from_dict(event["step"]))

        if run is None:
            raise ValueError(f"run file has no creation event: {run_id}")
        return run

    def list_runs(self) -> list[RunRecord]:
        if not self.run_dir.exists():
            return []
        return [self.get_run(path.stem) for path in sorted(self.run_dir.glob("*.jsonl"))]

    def _append_event(self, path: Path, event: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        safe_event = _redact_sensitive(event)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(safe_event, sort_keys=True))
            stream.write("\n")

    def _path_for(self, run_id: str) -> Path:
        if not run_id or Path(run_id).name != run_id or "/" in run_id or "\\" in run_id:
            raise ValueError("run_id must be a non-empty file name")
        return self.run_dir / f"{run_id}.jsonl"


def _redact_sensitive(value: object, sensitive_context: bool = False) -> object:
    if isinstance(value, dict):
        return {
            key: _redact_sensitive(item, sensitive_context or _is_sensitive_key(str(key)))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive(item, sensitive_context) for item in value]
    if isinstance(value, str):
        if sensitive_context:
            return _REDACTED
        return _redact_text(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold()
    return any(marker in normalized for marker in _SENSITIVE_KEY_MARKERS)


def _contains_sensitive_reference(value: str) -> bool:
    normalized = value.casefold()
    return "openai_api_key" in normalized or "api_key=" in normalized


def _redact_text(value: str) -> str:
    redacted = _REDACTED if _contains_sensitive_reference(value) else value
    for pattern in _SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(_pattern_replacement, redacted)
    return redacted


def _pattern_replacement(match: re.Match[str]) -> str:
    if match.lastindex == 2:
        return f"{match.group(1)}{_REDACTED}{match.group(2)}"
    if match.lastindex == 1:
        return f"{match.group(1)}={_REDACTED}"
    return _REDACTED


def _run_record_from_dict(data: dict[str, Any]) -> RunRecord:
    return RunRecord(
        id=data["id"],
        project_root=data["project_root"],
        status=RunStatus(data.get("status", RunStatus.RUNNING.value)),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        max_rounds=data.get("max_rounds", 3),
        current_round=data.get("current_round", 0),
        steps=[_run_step_from_dict(step) for step in data.get("steps", [])],
        final_summary=data.get("final_summary", ""),
    )


def _run_step_from_dict(data: dict[str, Any]) -> RunStep:
    return RunStep(
        run_id=data["run_id"],
        round_index=data["round_index"],
        llm_backend=data.get("llm_backend", ""),
        context_summary=data.get("context_summary", ""),
        action=_action_from_dict(data.get("action")),
        guardrail_decision=_guardrail_from_dict(data.get("guardrail_decision")),
        tool_result=_tool_result_from_dict(data.get("tool_result")),
        feedback=_failure_summary_from_dict(data.get("feedback")),
        created_at=data.get("created_at", ""),
    )


def _action_from_dict(data: dict[str, Any] | None) -> Action | None:
    if data is None:
        return None
    return Action(
        type=ActionType(data["type"]),
        payload=data.get("payload", {}),
        raw_model_output=data.get("raw_model_output", ""),
        parse_status=ActionParseStatus(data.get("parse_status", ActionParseStatus.PARSED.value)),
    )


def _guardrail_from_dict(data: dict[str, Any] | None) -> GuardrailDecision | None:
    if data is None:
        return None
    return GuardrailDecision(
        decision=GuardrailDecisionType(data["decision"]),
        policy_code=data.get("policy_code", ""),
        reason=data.get("reason", ""),
        risk_level=data.get("risk_level", "low"),
    )


def _tool_result_from_dict(data: dict[str, Any] | None) -> ToolResult | None:
    if data is None:
        return None
    return ToolResult(
        tool_name=data["tool_name"],
        success=data.get("success", False),
        stdout_summary=data.get("stdout_summary", ""),
        stderr_summary=data.get("stderr_summary", ""),
        exit_code=data.get("exit_code"),
        changed_files=data.get("changed_files", []),
        error=data.get("error", ""),
        test_result=_test_result_from_dict(data.get("test_result")),
        patch_record=_patch_record_from_dict(data.get("patch_record")),
    )


def _test_result_from_dict(data: dict[str, Any] | None) -> TestResult | None:
    if data is None:
        return None
    return TestResult(
        command=data.get("command", []),
        exit_code=data.get("exit_code", 0),
        duration_ms=data.get("duration_ms", 0),
        timed_out=data.get("timed_out", False),
        stdout=data.get("stdout", ""),
        stderr=data.get("stderr", ""),
        raw_output_ref=data.get("raw_output_ref", ""),
        failure_summary=_failure_summary_from_dict(data.get("failure_summary")),
    )


def _patch_record_from_dict(data: dict[str, Any] | None) -> PatchRecord | None:
    if data is None:
        return None
    return PatchRecord(
        files_changed=data.get("files_changed", []),
        diff=data.get("diff", ""),
        applied=data.get("applied", False),
        requires_approval=data.get("requires_approval", False),
        source_step=data.get("source_step"),
    )


def _failure_summary_from_dict(data: dict[str, Any] | None) -> FailureSummary | None:
    if data is None:
        return None
    return FailureSummary(
        status=TestStatus(data.get("status", TestStatus.FAILED.value)),
        category=FailureCategory(data.get("category", FailureCategory.UNKNOWN_FAILURE.value)),
        failed_tests=data.get("failed_tests", []),
        related_files=data.get("related_files", []),
        traceback_excerpt=data.get("traceback_excerpt", ""),
        line_hints=data.get("line_hints", []),
        message=data.get("message", ""),
    )
