from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrepair.models import LLMProvider, RunStatus


runner = CliRunner()


def test_repair_config_has_safe_demo_defaults(tmp_path: Path) -> None:
    from pyrepair.config import RepairConfig
    from pyrepair.store import JsonlRunStore

    config = RepairConfig(run_store=JsonlRunStore(tmp_path / "runs"))

    assert config.max_rounds == 3
    assert config.pytest_command == ["python", "-m", "pytest"]
    assert config.pytest_timeout_seconds > 0
    assert config.llm_provider is LLMProvider.MOCK
    assert RepairConfig(
        run_store=JsonlRunStore(tmp_path / "openai-runs"),
        llm_provider=LLMProvider.OPENAI_COMPATIBLE,
    ).llm_provider is LLMProvider.OPENAI_COMPATIBLE


def test_run_controller_rejects_unconfigured_openai_compatible_provider(tmp_path: Path) -> None:
    from pyrepair.config import RepairConfig
    from pyrepair.run_controller import RunController
    from pyrepair.store import JsonlRunStore

    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="OpenAI-compatible"):
        RunController().start_run(
            project_root,
            RepairConfig(
                run_store=JsonlRunStore(tmp_path / "runs"),
                llm_provider=LLMProvider.OPENAI_COMPATIBLE,
            ),
        )


def test_run_controller_delegates_to_injected_core_loop_for_openai_provider(
    tmp_path: Path,
) -> None:
    from pyrepair.config import RepairConfig
    from pyrepair.run_controller import RunController
    from pyrepair.store import JsonlRunStore

    class RecordingCoreLoop:
        def run(self, project_root: Path, config: RepairConfig):
            from pyrepair.models import RunRecord

            return RunRecord(id="run-controller", project_root=str(project_root), status=RunStatus.PASSED)

    project_root = tmp_path / "project"
    project_root.mkdir()
    run = RunController(core_loop=RecordingCoreLoop()).start_run(
        project_root,
        RepairConfig(
            run_store=JsonlRunStore(tmp_path / "runs"),
            llm_provider=LLMProvider.OPENAI_COMPATIBLE,
        ),
    )

    assert run.status is RunStatus.PASSED
    assert run.project_root == str(project_root.resolve())


def test_feedback_loop_demo_reports_passed_final_status() -> None:
    from pyrepair.cli import app

    result = runner.invoke(app, ["demo", "feedback-loop"])

    assert result.exit_code == 0, result.output
    assert "final status: PASSED" in result.output


def test_guardrail_demo_reports_approval_required_status() -> None:
    from pyrepair.cli import app

    result = runner.invoke(app, ["demo", "guardrail"])

    assert result.exit_code == 0, result.output
    assert "approval_required" in result.output
    assert "final status: WAITING_APPROVAL" in result.output


def test_key_commands_store_and_report_without_printing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from pyrepair import cli
    from pyrepair.credentials import CredentialStore, InMemoryCredentialBackend

    store = CredentialStore(InMemoryCredentialBackend())
    secret = "sk-test-only-cli-secret-123456"
    monkeypatch.setattr(cli, "get_credential_store", lambda: store)

    set_result = runner.invoke(
        cli.app,
        ["key", "set", "--provider", "openai"],
        input=f"{secret}\n",
    )
    status_result = runner.invoke(cli.app, ["key", "status", "--provider", "openai"])
    clear_result = runner.invoke(cli.app, ["key", "clear", "--provider", "openai"])

    assert set_result.exit_code == 0, set_result.output
    assert status_result.exit_code == 0, status_result.output
    assert clear_result.exit_code == 0, clear_result.output
    assert secret not in set_result.output
    assert secret not in status_result.output
    assert secret not in clear_result.output
    assert "configured" in status_result.output
    assert store.get_key("openai") is None
