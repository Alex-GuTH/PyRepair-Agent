"""Typer commands for local repair runs and deterministic demos."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import typer

from pyrepair.config import RepairConfig
from pyrepair.llm import MockLLMClient
from pyrepair.models import RunRecord
from pyrepair.run_controller import RunController
from pyrepair.store import JsonlRunStore


app = typer.Typer(help="Run guarded pytest repair workflows.", no_args_is_help=True)
demo_app = typer.Typer(help="Run deterministic offline demos.", no_args_is_help=True)
app.add_typer(demo_app, name="demo")

_FIXTURE_ROOT = Path(__file__).parents[2] / "examples" / "buggy_calculator"


@app.command()
def run(project_path: Path) -> None:
    """Run a local project with the default offline mock backend."""
    try:
        record = RunController().start_run(
            project_path,
            RepairConfig(run_store=JsonlRunStore(project_path.resolve() / ".pyrepair-runs")),
        )
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="project_path") from None
    _print_run(record)


@demo_app.command("feedback-loop")
def feedback_loop_demo() -> None:
    """Repair the bundled calculator fixture with a scripted mock LLM."""
    record = _run_demo(_feedback_script())
    _print_run(record)


@demo_app.command("guardrail")
def guardrail_demo() -> None:
    """Attempt a protected test-file edit and stop for approval."""
    record = _run_demo(_guardrail_script())
    _print_run(record)


@demo_app.command("full")
def full_demo() -> None:
    """Run both deterministic demos."""
    typer.echo("feedback-loop")
    _print_run(_run_demo(_feedback_script()))
    typer.echo("guardrail")
    _print_run(_run_demo(_guardrail_script()))


@app.command()
def web() -> None:
    """Reserve the WebUI command for Task 13."""
    typer.echo("WebUI is not available until Task 13.", err=True)
    raise typer.Exit(code=1)


def _run_demo(script: list[str]) -> RunRecord:
    with tempfile.TemporaryDirectory(prefix="pyrepair-demo-") as temp_dir:
        project_root = Path(temp_dir) / "buggy_calculator"
        shutil.copytree(_FIXTURE_ROOT, project_root)
        config = RepairConfig(run_store=JsonlRunStore(Path(temp_dir) / "runs"))
        return RunController(MockLLMClient(script)).start_run(project_root, config)


def _feedback_script() -> list[str]:
    return [
        _action("READ_FILE", {"path": "src/calculator.py"}),
        _action(
            "APPLY_PATCH",
            {
                "path": "src/calculator.py",
                "diff": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -2 +2 @@\n-    return left - right\n+    return left * right\n",
            },
        ),
        _action(
            "APPLY_PATCH",
            {
                "path": "src/calculator.py",
                "diff": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -2 +2 @@\n-    return left * right\n+    return left + right\n",
            },
        ),
    ]


def _guardrail_script() -> list[str]:
    return [
        _action(
            "APPLY_PATCH",
            {
                "path": "tests/test_calculator.py",
                "diff": "--- a/tests/test_calculator.py\n+++ b/tests/test_calculator.py\n@@ -10 +10 @@\n-    assert add(1, 2) == 3\n+    assert add(1, 2) == -1\n",
            },
        )
    ]


def _action(action_type: str, payload: dict[str, object]) -> str:
    return json.dumps({"type": action_type, "payload": payload})


def _print_run(record: RunRecord) -> None:
    typer.echo(f"run id: {record.id}")
    for step in record.steps:
        if step.feedback is not None:
            typer.echo(f"feedback: {step.feedback.category.value}")
        if step.guardrail_decision is not None:
            typer.echo(f"guardrail: {step.guardrail_decision.decision.value.lower()}")
    typer.echo(f"final status: {record.status.value}")
    typer.echo(f"summary: {record.final_summary}")
