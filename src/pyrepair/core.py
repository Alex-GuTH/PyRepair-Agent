"""The deterministic core loop for source-only pytest repairs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pyrepair.actions import ActionParseError, parse_action
from pyrepair.feedback import parse_pytest_feedback
from pyrepair.guardrails import GuardrailPolicy, evaluate_action
from pyrepair.llm import LLMClient
from pyrepair.models import (
    Action,
    ActionType,
    FailureCategory,
    FailureSummary,
    GuardrailDecision,
    GuardrailDecisionType,
    RunRecord,
    RunStatus,
    RunStep,
    TestResult,
    TestStatus,
    ToolResult,
)
from pyrepair.store import JsonlRunStore
from pyrepair.tools import PatchApplier, ProjectScanner, PytestRunner, SafeFileReader


@dataclass
class RepairConfig:
    """Dependencies and limits for a single repair run."""

    run_store: JsonlRunStore
    max_rounds: int = 3
    pytest_command: list[str] = field(
        default_factory=lambda: ["python", "-m", "pytest"]
    )
    pytest_timeout_seconds: int = 30
    guardrail_policy: GuardrailPolicy = field(default_factory=GuardrailPolicy)


class AgentCoreLoop:
    """Run a guarded, feedback-driven repair conversation against one project."""

    def __init__(
        self,
        llm_client: LLMClient,
        *,
        scanner: ProjectScanner | None = None,
        pytest_runner: PytestRunner | None = None,
        file_reader: SafeFileReader | None = None,
        patch_applier: PatchApplier | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._scanner = scanner or ProjectScanner()
        self._pytest_runner = pytest_runner or PytestRunner()
        self._file_reader = file_reader or SafeFileReader()
        self._patch_applier = patch_applier or PatchApplier()

    def run(self, project_root: Path, config: RepairConfig) -> RunRecord:
        """Attempt a bounded repair run and return its in-memory record."""
        root = project_root.resolve()
        run = RunRecord(
            id=f"run-{uuid4().hex}",
            project_root=str(root),
            created_at=_timestamp(),
            updated_at=_timestamp(),
            max_rounds=config.max_rounds,
        )
        config.run_store.create_run(run)

        scan = self._scanner.scan(root)
        self._append_step(
            run,
            config,
            RunStep(
                run_id=run.id,
                round_index=0,
                llm_backend=_backend_name(self._llm_client),
                context_summary="Initial project scan.",
                action=Action(type=ActionType.PROJECT_SCAN),
                tool_result=ToolResult(
                    tool_name="project_scanner",
                    success=True,
                    stdout_summary=json.dumps(scan, sort_keys=True),
                ),
                created_at=_timestamp(),
            ),
        )

        feedback = self._run_tests(run, config, round_index=0)
        if feedback.category is FailureCategory.NONE:
            return self._finish(run, config, RunStatus.PASSED, "Initial pytest run passed.")

        last_feedback = feedback
        read_files: dict[str, str] = {}
        for round_index in range(1, config.max_rounds + 1):
            run.current_round = round_index
            context = self._build_context(scan, last_feedback, read_files)
            try:
                action = parse_action(self._llm_client.generate(context))
            except (ActionParseError, RuntimeError) as error:
                self._append_step(
                    run,
                    config,
                    RunStep(
                        run_id=run.id,
                        round_index=round_index,
                        llm_backend=_backend_name(self._llm_client),
                        context_summary=_context_summary(scan, last_feedback),
                        tool_result=ToolResult(
                            tool_name="action_parser",
                            error=str(error),
                        ),
                        feedback=last_feedback,
                        created_at=_timestamp(),
                    ),
                )
                return self._finish(run, config, RunStatus.FAILED, "Unable to obtain a valid action.")

            decision = evaluate_action(action, root, config.guardrail_policy)
            if decision.decision is GuardrailDecisionType.APPROVAL_REQUIRED:
                self._append_step(
                    run,
                    config,
                    self._guardrail_step(run, round_index, action, decision, last_feedback),
                )
                return self._finish(
                    run,
                    config,
                    RunStatus.WAITING_APPROVAL,
                    decision.reason,
                )
            if decision.decision is GuardrailDecisionType.REJECT:
                self._append_step(
                    run,
                    config,
                    self._guardrail_step(run, round_index, action, decision, last_feedback),
                )
                return self._finish(run, config, RunStatus.FAILED, decision.reason)

            tool_result, read_value = self._dispatch(action, root, config)
            if read_value is not None:
                read_files[str(action.payload["path"])] = read_value
            self._append_step(
                run,
                config,
                RunStep(
                    run_id=run.id,
                    round_index=round_index,
                    llm_backend=_backend_name(self._llm_client),
                    context_summary=_context_summary(scan, last_feedback),
                    action=action,
                    guardrail_decision=decision,
                    tool_result=tool_result,
                    feedback=last_feedback,
                    created_at=_timestamp(),
                ),
            )

            if not tool_result.success:
                last_feedback = FailureSummary(
                    category=FailureCategory.UNKNOWN_FAILURE,
                    message=tool_result.error or "Action tool failed.",
                )
                continue
            if action.type is ActionType.FINISH:
                return self._finish(run, config, RunStatus.FAILED, "Agent finished before tests passed.")
            if action.type is ActionType.APPLY_PATCH:
                last_feedback = self._run_tests(run, config, round_index=round_index)
                if last_feedback.category is FailureCategory.NONE:
                    return self._finish(run, config, RunStatus.PASSED, "Pytest passed after patch.")
            elif action.type is ActionType.RUN_TESTS:
                last_feedback = tool_result.test_result.failure_summary  # type: ignore[union-attr]
                if last_feedback.category is FailureCategory.NONE:
                    return self._finish(run, config, RunStatus.PASSED, "Pytest passed.")

        return self._finish(run, config, RunStatus.FAILED, "Maximum repair rounds reached.")

    def _run_tests(
        self,
        run: RunRecord,
        config: RepairConfig,
        *,
        round_index: int,
    ) -> FailureSummary:
        action = Action(
            type=ActionType.RUN_TESTS,
            payload={"command": list(config.pytest_command)},
        )
        result = self._pytest_runner.run(
            Path(run.project_root), config.pytest_command, config.pytest_timeout_seconds
        )
        feedback = _feedback_for(result)
        result.failure_summary = feedback
        self._append_step(
            run,
            config,
            RunStep(
                run_id=run.id,
                round_index=round_index,
                llm_backend=_backend_name(self._llm_client),
                context_summary="Pytest verification.",
                action=action,
                guardrail_decision=evaluate_action(
                    action, Path(run.project_root), config.guardrail_policy
                ),
                tool_result=_test_tool_result(result),
                feedback=feedback,
                created_at=_timestamp(),
            ),
        )
        return feedback

    def _dispatch(
        self,
        action: Action,
        project_root: Path,
        config: RepairConfig,
    ) -> tuple[ToolResult, str | None]:
        try:
            if action.type is ActionType.PROJECT_SCAN:
                scan = self._scanner.scan(project_root)
                return ToolResult("project_scanner", success=True, stdout_summary=json.dumps(scan)), None
            if action.type is ActionType.READ_FILE:
                path = action.payload["path"]
                content = self._file_reader.read(project_root, str(path))
                return ToolResult("safe_file_reader", success=True, stdout_summary=content), content
            if action.type is ActionType.APPLY_PATCH:
                diff = action.payload.get("diff")
                if not isinstance(diff, str):
                    raise ValueError("APPLY_PATCH requires a string diff")
                patch_record = self._patch_applier.apply_unified_diff(project_root, diff)
                return ToolResult(
                    "patch_applier",
                    success=True,
                    changed_files=patch_record.files_changed,
                    patch_record=patch_record,
                ), None
            if action.type is ActionType.RUN_TESTS:
                result = self._pytest_runner.run(
                    project_root, config.pytest_command, config.pytest_timeout_seconds
                )
                result.failure_summary = _feedback_for(result)
                return _test_tool_result(result), None
            if action.type is ActionType.FINISH:
                return ToolResult("finish", success=True), None
        except (OSError, ValueError) as error:
            return ToolResult(tool_name=action.type.value.lower(), error=str(error)), None
        return ToolResult(tool_name=action.type.value.lower(), error="Unsupported action."), None

    def _guardrail_step(
        self,
        run: RunRecord,
        round_index: int,
        action: Action,
        decision: GuardrailDecision,
        feedback: FailureSummary,
    ) -> RunStep:
        return RunStep(
            run_id=run.id,
            round_index=round_index,
            llm_backend=_backend_name(self._llm_client),
            context_summary="Guardrail evaluation.",
            action=action,
            guardrail_decision=decision,
            tool_result=ToolResult(
                tool_name="guardrails",
                error=decision.reason,
            ),
            feedback=feedback,
            created_at=_timestamp(),
        )

    @staticmethod
    def _append_step(run: RunRecord, config: RepairConfig, step: RunStep) -> None:
        run.steps.append(step)
        config.run_store.append_step(run.id, step)

    @staticmethod
    def _build_context(
        scan: dict[str, list[str]],
        feedback: FailureSummary,
        read_files: dict[str, str],
    ) -> list[dict[str, str]]:
        payload = {
            "project": scan,
            "feedback": {
                "category": feedback.category.value,
                "failed_tests": feedback.failed_tests,
                "related_files": feedback.related_files,
                "message": feedback.message,
            },
            "read_files": read_files,
        }
        return [
            {
                "role": "system",
                "content": "Return one JSON repair action. Only source Python patches are automatic.",
            },
            {"role": "user", "content": json.dumps(payload, sort_keys=True)},
        ]

    @staticmethod
    def _finish(
        run: RunRecord,
        config: RepairConfig,
        status: RunStatus,
        summary: str,
    ) -> RunRecord:
        run.status = status
        run.final_summary = summary
        run.updated_at = _timestamp()
        config.run_store.finish_run(run)
        return run


def _feedback_for(result: TestResult) -> FailureSummary:
    if result.exit_code == 0 and not result.timed_out:
        return FailureSummary(status=TestStatus.PASSED, category=FailureCategory.NONE)
    return parse_pytest_feedback(result)


def _test_tool_result(result: TestResult) -> ToolResult:
    return ToolResult(
        tool_name="pytest",
        success=result.exit_code == 0 and not result.timed_out,
        stdout_summary=result.stdout,
        stderr_summary=result.stderr,
        exit_code=result.exit_code,
        test_result=result,
    )


def _backend_name(client: LLMClient) -> str:
    return client.__class__.__name__


def _context_summary(scan: dict[str, list[str]], feedback: FailureSummary) -> str:
    return (
        f"{len(scan['source_files'])} source files, {len(scan['test_files'])} test files; "
        f"latest feedback: {feedback.category.value}."
    )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
