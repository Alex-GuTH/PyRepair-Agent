from __future__ import annotations

import json
import shutil
from pathlib import Path

from pyrepair.llm import MockLLMClient
from pyrepair.models import ActionType, FailureCategory, RunStatus
from pyrepair.store import JsonlRunStore


FIXTURE_ROOT = Path(__file__).parents[1] / "examples" / "buggy_calculator"


def _copy_calculator_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "buggy_calculator"
    shutil.copytree(FIXTURE_ROOT, project_root)
    return project_root


def _action(action_type: str, payload: dict[str, object]) -> str:
    return json.dumps({"type": action_type, "payload": payload})


def test_core_loop_uses_assertion_feedback_to_repair_source_file(tmp_path: Path) -> None:
    from pyrepair.core import AgentCoreLoop, RepairConfig

    project_root = _copy_calculator_project(tmp_path)
    store = JsonlRunStore(tmp_path / "runs")
    client = MockLLMClient(
        [
            _action("READ_FILE", {"path": "src/calculator.py"}),
            _action(
                "APPLY_PATCH",
                {
                    "path": "src/calculator.py",
                    "diff": "--- a/src/calculator.py\n"
                    "+++ b/src/calculator.py\n"
                    "@@ -2 +2 @@\n"
                    "-    return left - right\n"
                    "+    return left * right\n",
                },
            ),
            _action(
                "APPLY_PATCH",
                {
                    "path": "src/calculator.py",
                    "diff": "--- a/src/calculator.py\n"
                    "+++ b/src/calculator.py\n"
                    "@@ -2 +2 @@\n"
                    "-    return left * right\n"
                    "+    return left + right\n",
                },
            ),
        ]
    )

    run = AgentCoreLoop(client).run(
        project_root,
        RepairConfig(run_store=store, max_rounds=3),
    )

    initial_test_step = next(
        step
        for step in run.steps
        if step.action is not None and step.action.type is ActionType.RUN_TESTS
    )
    assert initial_test_step.tool_result is not None
    assert initial_test_step.tool_result.test_result is not None
    assert initial_test_step.tool_result.test_result.exit_code != 0
    assert any(
        step.feedback is not None
        and step.feedback.category is FailureCategory.ASSERTION_FAILURE
        for step in run.steps
    )
    assert run.status is RunStatus.PASSED
    assert "return left + right" in (project_root / "src" / "calculator.py").read_text(
        encoding="utf-8"
    )
    assert len(store.get_run(run.id).steps) > 1


def test_core_loop_waits_for_approval_before_changing_test_file(tmp_path: Path) -> None:
    from pyrepair.core import AgentCoreLoop, RepairConfig

    project_root = _copy_calculator_project(tmp_path)
    test_file = project_root / "tests" / "test_calculator.py"
    original_test = test_file.read_text(encoding="utf-8")
    store = JsonlRunStore(tmp_path / "runs")
    client = MockLLMClient(
        [
            _action(
                "APPLY_PATCH",
                {
                    "path": "tests/test_calculator.py",
                    "diff": "--- a/tests/test_calculator.py\n"
                    "+++ b/tests/test_calculator.py\n"
                    "@@ -10 +10 @@\n"
                    "-    assert add(1, 2) == 3\n"
                    "+    assert add(1, 2) == -1\n",
                },
            )
        ]
    )

    run = AgentCoreLoop(client).run(project_root, RepairConfig(run_store=store))

    assert run.status is RunStatus.WAITING_APPROVAL
    assert test_file.read_text(encoding="utf-8") == original_test
    assert any(
        step.action is not None
        and step.action.type is ActionType.APPLY_PATCH
        and step.guardrail_decision is not None
        and step.guardrail_decision.policy_code == "protected_write_approval_required"
        for step in run.steps
    )
